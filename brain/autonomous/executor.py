"""
Autonomous execution engine for T — Phase 12.

Receives a goal → plans → executes steps → only confirms HIGH/CRITICAL →
builds working memory → generates report → done.

Communication model: progress updates only (step name + status + one-line summary).
Raw output stored in memory but not streamed unless user asks.
"""

import asyncio
import re
import time
from typing import TYPE_CHECKING
from core.logger import get_logger
from .memory     import WorkingMemory
from .planner    import detect_task_type, next_step, STEP_TEMPLATES
from .tool_bridge import run_tool, requires_confirmation, all_tools
from .reporter   import generate as generate_report

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("autonomous.executor")

MAX_STEPS   = 30      # hard cap
MAX_SILENT  = 10      # max consecutive LOW/MEDIUM steps before a status ping

# Active tasks: task_id → asyncio.Task
_active_tasks: dict[str, asyncio.Task]      = {}
# Pending confirmations: task_id → Future[bool]
_pending_confirms: dict[str, asyncio.Future] = {}


# ── Entry points ───────────────────────────────────────────────────────────────

async def start_task(client: "Client", msg: dict) -> None:
    """
    Start an autonomous task. Non-blocking — runs as a background asyncio task.
    msg: { id, goal, target? }
    """
    task_id = msg.get("id", "")
    goal    = msg.get("goal", "").strip()

    if not goal:
        await _emit(client, task_id, "auto_error", {"error": "No goal provided"})
        return

    # Auto-detect task type and target
    task_type, target = detect_task_type(goal)
    explicit_target   = msg.get("target", "").strip()
    if explicit_target:
        target = explicit_target

    mem = WorkingMemory(goal=goal, target=target, task_type=task_type)

    await _emit(client, task_id, "auto_started", {
        "goal":      goal,
        "target":    target,
        "task_type": task_type,
        "max_steps": MAX_STEPS,
    })

    task = asyncio.create_task(_run(client, task_id, mem))
    _active_tasks[task_id] = task


async def stop_task(client: "Client", msg: dict) -> None:
    """Cancel a running autonomous task."""
    task_id = msg.get("id", "")
    task    = _active_tasks.pop(task_id, None)
    if task:
        task.cancel()
        await _emit(client, task_id, "auto_stopped", {"message": "Task stopped by user"})
    # Resolve any pending confirmation as denied
    fut = _pending_confirms.pop(task_id, None)
    if fut and not fut.done():
        fut.set_result(False)


async def confirm_step(client: "Client", msg: dict) -> None:
    """User confirmed or denied a HIGH/CRITICAL step."""
    task_id   = msg.get("id", "")
    confirmed = bool(msg.get("confirmed", False))
    fut = _pending_confirms.pop(task_id, None)
    if fut and not fut.done():
        fut.set_result(confirmed)


# ── Main execution loop ────────────────────────────────────────────────────────

async def _run(client: "Client", task_id: str, mem: WorkingMemory) -> None:
    profile = {}
    try:
        from core.engine import _profiles
        profile = next(iter(_profiles.values()), {})
    except Exception:
        pass

    groq_key = profile.get("groqKey", "")
    tools    = all_tools()

    step_count   = 0
    silent_count = 0
    completed_tools: set[str] = set()

    try:
        # Use template steps as a starting queue, then switch to LLM planning
        template = STEP_TEMPLATES.get(mem.task_type, STEP_TEMPLATES["audit"])
        step_queue = list(template)   # shallow copy

        while step_count < MAX_STEPS:
            # ── Decide next action ────────────────────────────────────────────
            if step_queue:
                # Use template until queue exhausted
                next_action = step_queue.pop(0)
                next_action.setdefault("done", False)
            else:
                # Switch to LLM-driven planning
                next_action = await next_step(mem, groq_key, tools)

            if next_action is None:
                # LLM couldn't decide — stop
                break

            if next_action.get("done"):
                summary = next_action.get("summary", "Task complete.")
                await _finish(client, task_id, mem, summary)
                return

            tool      = next_action.get("tool", "")
            params    = next_action.get("params", {})
            step_name = next_action.get("name") or next_action.get("step_name", tool)
            reason    = next_action.get("reason", next_action.get("desc", ""))

            # Skip already-succeeded tools (except report)
            if tool in completed_tools and tool != "generate_report":
                continue

            # ── Confirmation gate for HIGH/CRITICAL ───────────────────────────
            if requires_confirmation(tool):
                await _emit(client, task_id, "auto_confirm_request", {
                    "step":   step_name,
                    "tool":   tool,
                    "reason": reason,
                    "risk":   "HIGH" if tool not in ("vm_cred_dump", "vm_hashdump", "vm_persistence") else "CRITICAL",
                })

                loop = asyncio.get_event_loop()
                fut: asyncio.Future = loop.create_future()
                _pending_confirms[task_id] = fut

                try:
                    confirmed = await asyncio.wait_for(fut, timeout=120.0)
                except asyncio.TimeoutError:
                    confirmed = False
                finally:
                    _pending_confirms.pop(task_id, None)

                if not confirmed:
                    mem.add_step(step_name, tool, "skipped", "User declined")
                    await _emit(client, task_id, "auto_step", {
                        "step": step_name, "tool": tool, "status": "skipped",
                        "summary": "Declined by user",
                    })
                    continue

            # ── Execute tool ──────────────────────────────────────────────────
            step_count  += 1
            silent_count += 1
            started      = time.time()

            await _emit(client, task_id, "auto_step", {
                "step":    step_name,
                "tool":    tool,
                "status":  "running",
                "summary": reason,
                "step_n":  step_count,
            })

            # Collect output
            output_lines: list[str] = []
            try:
                async for line in run_tool(tool, params, mem.target):
                    output_lines.append(line)
            except Exception as e:
                output_lines.append(f"[ERROR] {e}")

            raw_output = "\n".join(output_lines)
            duration   = round(time.time() - started, 1)

            # ── Parse output → working memory ─────────────────────────────────
            summary = _parse_into_memory(mem, tool, step_name, raw_output)
            status  = "error" if raw_output.strip().startswith("[ERROR]") else "done"

            mem.add_step(step_name, tool, status, summary, raw_output)
            completed_tools.add(tool)

            await _emit(client, task_id, "auto_step", {
                "step":     step_name,
                "tool":     tool,
                "status":   status,
                "summary":  summary,
                "duration": duration,
                "step_n":   step_count,
                "memory":   mem.to_dict(),
            })

            # Periodic status ping
            if silent_count >= MAX_SILENT:
                silent_count = 0
                await _emit(client, task_id, "auto_status", {
                    "message": f"Step {step_count}/{MAX_STEPS} — {len(mem.findings)} findings so far",
                    "memory":  mem.to_dict(),
                })

            # Special: generate_report means we're done
            if tool == "generate_report":
                break

        # Ran out of steps or hit limit
        await _finish(client, task_id, mem, _auto_summary(mem))

    except asyncio.CancelledError:
        pass
    except Exception as e:
        log.error(f"autonomous executor error: {e}")
        await _emit(client, task_id, "auto_error", {"error": str(e)})
    finally:
        _active_tasks.pop(task_id, None)


# ── Finish ────────────────────────────────────────────────────────────────────

async def _finish(client: "Client", task_id: str,
                  mem: WorkingMemory, summary: str) -> None:
    """Generate report and emit auto_done."""
    try:
        report_path = generate_report(mem, summary)
    except Exception as e:
        report_path = ""
        log.warning(f"report generation failed: {e}")

    await _emit(client, task_id, "auto_done", {
        "summary":     summary,
        "report_path": report_path,
        "memory":      mem.to_dict(),
        "duration":    int(time.time() - mem.start_ts),
    })


# ── Output parser ─────────────────────────────────────────────────────────────

def _parse_into_memory(mem: WorkingMemory, tool: str,
                        step: str, output: str) -> str:
    """
    Parse tool output into working memory.
    Returns a one-line summary of what was found.
    """
    lines   = output.splitlines()
    found   = []

    # Nmap — extract open ports and services
    if tool in ("nmap_quick", "nmap_full", "nmap_scripts"):
        ports = []
        for line in lines:
            m = re.match(r"(\d+)/tcp\s+open\s+(\S+)\s*(.*)", line)
            if m:
                port = int(m.group(1))
                svc  = m.group(2)
                ver  = m.group(3).strip()
                ports.append(port)
                mem.add_finding(step, tool, "open_ports", [port])
                mem.add_finding(step, tool, "service",
                                {"port": port, "service": svc, "version": ver,
                                 "desc": f"{port}/{svc} {ver}"})
        if ports:
            found.append(f"{len(ports)} open ports: {', '.join(str(p) for p in sorted(ports)[:8])}")
        else:
            found.append("No open ports found")

    # Subdomains
    elif tool in ("vm_subfinder", "vm_amass"):
        subs = [l.strip() for l in lines if "." in l and not l.startswith("[") and l.strip()]
        for s in subs[:30]:
            mem.add_finding(step, tool, "subdomain", s)
        if subs:
            found.append(f"{len(subs)} subdomains")

    # Nuclei — CVEs
    elif tool == "vm_nuclei":
        vulns = [l for l in lines if "[" in l and "]" in l and l.strip()]
        for v in vulns[:20]:
            sev = "medium"
            if "critical" in v.lower(): sev = "critical"
            elif "high" in v.lower():   sev = "high"
            elif "low" in v.lower():    sev = "low"
            mem.add_finding(step, tool, "vuln", {"desc": v.strip()}, sev)
        if vulns:
            found.append(f"{len(vulns)} vulnerabilities detected")
        else:
            found.append("No vulnerabilities found")

    # Flags
    elif tool == "vm_flag_search":
        flag_re = re.compile(r"[A-Za-z0-9_\-]+\{[A-Za-z0-9_\-=+/!@#$%^&*]{8,}\}")
        for m_obj in flag_re.finditer(output):
            flag = m_obj.group(0)
            mem.add_finding(step, tool, "flag", flag, "critical")
            found.append(f"FLAG: {flag}")

    # Emails / social
    elif tool in ("vm_theharvester", "intel_email", "intel_username"):
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", output)
        for e in set(emails[:20]):
            mem.add_finding(step, tool, "email", e)
        social_hits = [l for l in lines if "[+]" in l or "✓" in l]
        for s in social_hits[:20]:
            platform = re.search(r"\[.\]\s+(\S+)", s)
            if platform:
                mem.add_finding(step, tool, "social",
                                {"platform": platform.group(1), "line": s.strip()})
        if emails or social_hits:
            parts = []
            if emails:      parts.append(f"{len(set(emails))} emails")
            if social_hits: parts.append(f"{len(social_hits)} social accounts")
            found.append(", ".join(parts))

    # Credentials / hashes
    elif tool in ("vm_cred_dump", "vm_hashdump", "vm_hydra"):
        cred_re = re.compile(r"[^:]+:[^:]+:[a-fA-F0-9]{32}", re.MULTILINE)
        creds = cred_re.findall(output)
        for c in creds[:20]:
            mem.add_finding(step, tool, "credential", {"raw": c}, "critical")
        if creds:
            found.append(f"{len(creds)} credentials/hashes")
        else:
            hydra_hits = [l for l in lines if "login:" in l.lower()]
            for h in hydra_hits[:10]:
                mem.add_finding(step, tool, "credential", {"raw": h}, "high")
            if hydra_hits:
                found.append(f"{len(hydra_hits)} credentials")

    # Searchsploit
    elif tool == "vm_searchsploit":
        exploits = [l for l in lines if "EDB-ID" in l or "|" in l]
        if exploits:
            found.append(f"{len(exploits)} exploit modules found")
            for e in exploits[:5]:
                mem.add_finding(step, tool, "vuln", {"desc": e.strip()}, "medium")

    # Breach
    elif tool in ("intel_breach",):
        hits = [l for l in lines if "breach" in l.lower() or "found" in l.lower()]
        for h in hits[:10]:
            mem.add_finding(step, tool, "breach", {"desc": h.strip()}, "high")
        if hits:
            found.append(f"{len(hits)} breach references")

    # Default
    if not found:
        non_empty = [l for l in lines if l.strip() and not l.startswith("[")]
        if non_empty:
            found.append(non_empty[0][:100])
        else:
            found.append("Completed")

    return "; ".join(found)


def _auto_summary(mem: WorkingMemory) -> str:
    """Generate a brief text summary from working memory."""
    parts = [f"Target: {mem.target}", f"Steps completed: {len(mem.steps)}"]

    if mem.hosts:        parts.append(f"Hosts: {', '.join(mem.hosts[:5])}")
    if mem.open_ports:
        for h, ports in list(mem.open_ports.items())[:3]:
            parts.append(f"Open ports ({h}): {', '.join(str(p) for p in sorted(ports)[:10])}")
    if mem.vulns:        parts.append(f"Vulnerabilities: {len(mem.vulns)}")
    if mem.creds:        parts.append(f"Credentials found: {len(mem.creds)}")
    if mem.flags:        parts.append(f"FLAGS: {', '.join(mem.flags)}")
    if mem.subdomains:   parts.append(f"Subdomains: {len(mem.subdomains)}")
    if mem.emails:       parts.append(f"Emails: {len(mem.emails)}")
    if mem.social_accounts: parts.append(f"Social accounts: {len(mem.social_accounts)}")

    return "\n".join(parts)


# ── Emit helper ───────────────────────────────────────────────────────────────

async def _emit(client: "Client", task_id: str, event: str, data: dict) -> None:
    try:
        await client.send({"type": event, "id": task_id, **data})
    except Exception as e:
        log.warning(f"emit failed: {e}")
