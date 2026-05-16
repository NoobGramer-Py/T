"""
Autonomous planner for T.
Two jobs:
  1. decompose_goal()  — given a user goal, produce an ordered plan
  2. next_step()       — given current memory, decide what to do next

Both use the LLM. The planner is purely advisory — the executor drives the loop.
"""

import json
import re
from typing import TYPE_CHECKING
from core.logger import get_logger
from .memory import WorkingMemory

if TYPE_CHECKING:
    pass

log = get_logger("autonomous.planner")


# ── Task type detection ────────────────────────────────────────────────────────

def detect_task_type(goal: str) -> tuple[str, str]:
    """
    Detect the type of autonomous task from the goal string.
    Returns (task_type, extracted_target).
    task_type: audit | osint_person | osint_org | ctf | attack | generic
    """
    g = goal.lower().strip()

    # Phone number
    phone = re.search(r"(\+?\d[\d\s\-().]{6,}\d)", goal)
    if phone and any(w in g for w in ("profile", "dossier", "who", "osint", "intel", "find")):
        return "osint_person", phone.group(1).strip()

    # CTF / HTB / THM
    ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", goal)
    if any(w in g for w in ("ctf", "htb", "hackthebox", "tryhackme", "thm", "flag", "root.txt", "user.txt")):
        return "ctf", ip_match.group(1) if ip_match else ""

    # Security audit
    domain_match = re.search(r"([a-zA-Z0-9-]+\.[a-zA-Z]{2,})", goal)
    if any(w in g for w in ("audit", "scan", "pentest", "assess", "vuln", "security test")):
        target = ip_match.group(1) if ip_match else (domain_match.group(1) if domain_match else "")
        return "audit", target

    # Full attack chain
    if any(w in g for w in ("attack", "exploit", "compromise", "hack", "pwn", "takeover")):
        target = ip_match.group(1) if ip_match else (domain_match.group(1) if domain_match else "")
        return "attack", target

    # Person/org OSINT
    if any(w in g for w in ("profile", "dossier", "osint", "intel", "find info", "research")):
        if domain_match:
            return "osint_org", domain_match.group(1)
        # Name-based
        return "osint_person", goal

    # Generic IP/domain
    if ip_match:
        return "audit", ip_match.group(1)
    if domain_match:
        return "audit", domain_match.group(1)

    return "generic", ""


# ── Step templates ─────────────────────────────────────────────────────────────
# Pre-defined step sequences per task type.
# The LLM can extend or reorder these based on findings.

STEP_TEMPLATES: dict[str, list[dict]] = {
    "audit": [
        {"name": "Port scan",         "tool": "nmap_quick",      "risk": "LOW",    "desc": "Fast port and service discovery"},
        {"name": "Full port scan",     "tool": "nmap_full",       "risk": "LOW",    "desc": "All 65535 ports"},
        {"name": "Web fingerprint",    "tool": "http_fingerprint", "risk": "LOW",    "desc": "Detect web tech and frameworks"},
        {"name": "Subdomain enum",     "tool": "vm_subfinder",    "risk": "LOW",    "desc": "Passive subdomain discovery"},
        {"name": "Directory fuzz",     "tool": "vm_ffuf",         "risk": "MEDIUM", "desc": "Hidden dirs and files"},
        {"name": "Vuln scan",          "tool": "vm_nuclei",       "risk": "MEDIUM", "desc": "CVE template scan"},
        {"name": "Web vuln scan",      "tool": "vm_nikto",        "risk": "MEDIUM", "desc": "Web server vulnerabilities"},
        {"name": "CVE lookup",         "tool": "vm_searchsploit", "risk": "LOW",    "desc": "Match services to known exploits"},
        {"name": "OSINT footprint",    "tool": "vm_theharvester", "risk": "LOW",    "desc": "Emails and subdomains"},
        {"name": "Report",             "tool": "generate_report", "risk": "LOW",    "desc": "Generate findings report"},
    ],
    "ctf": [
        {"name": "Port scan",          "tool": "nmap_quick",      "risk": "LOW",    "desc": "Discover open ports"},
        {"name": "Full port scan",     "tool": "nmap_full",       "risk": "LOW",    "desc": "All ports including high range"},
        {"name": "Service scripts",    "tool": "nmap_scripts",    "risk": "LOW",    "desc": "NSE scripts on open ports"},
        {"name": "Web fingerprint",    "tool": "http_fingerprint", "risk": "LOW",   "desc": "Identify web stack"},
        {"name": "Directory fuzz",     "tool": "vm_gobuster",     "risk": "MEDIUM", "desc": "Find hidden paths"},
        {"name": "Vuln scan",          "tool": "vm_nuclei",       "risk": "MEDIUM", "desc": "Automated CVE detection"},
        {"name": "Searchsploit",       "tool": "vm_searchsploit", "risk": "LOW",    "desc": "Find exploit modules"},
        {"name": "Exploit",            "tool": "vm_metasploit",   "risk": "HIGH",   "desc": "Run matched exploit module"},
        {"name": "Search flags",       "tool": "vm_flag_search",  "risk": "MEDIUM", "desc": "Find user.txt and root.txt"},
        {"name": "Privilege escalation","tool": "vm_privesc",     "risk": "HIGH",   "desc": "Escalate to root"},
    ],
    "attack": [
        {"name": "Network recon",      "tool": "nmap_quick",      "risk": "LOW",    "desc": "Initial target discovery"},
        {"name": "Deep port scan",     "tool": "nmap_full",       "risk": "LOW",    "desc": "Full port enumeration"},
        {"name": "Subdomain harvest",  "tool": "vm_subfinder",    "risk": "LOW",    "desc": "Expand attack surface"},
        {"name": "Web enum",           "tool": "vm_ffuf",         "risk": "MEDIUM", "desc": "Enumerate web content"},
        {"name": "Vuln identify",      "tool": "vm_nuclei",       "risk": "MEDIUM", "desc": "Find exploitable CVEs"},
        {"name": "Exploit",            "tool": "vm_metasploit",   "risk": "HIGH",   "desc": "Exploit highest confidence vuln"},
        {"name": "Post-exploit",       "tool": "vm_post_exploit", "risk": "HIGH",   "desc": "Enumerate as compromised user"},
        {"name": "Credential dump",    "tool": "vm_cred_dump",    "risk": "CRITICAL","desc": "Extract credentials"},
        {"name": "Persistence",        "tool": "vm_persistence",  "risk": "CRITICAL","desc": "Install persistence mechanism"},
        {"name": "Report",             "tool": "generate_report", "risk": "LOW",    "desc": "Document full attack chain"},
    ],
    "osint_person": [
        {"name": "Phone intel",        "tool": "intel_phone",     "risk": "LOW",    "desc": "Carrier, region, caller-ID"},
        {"name": "Social search",      "tool": "intel_username",  "risk": "LOW",    "desc": "Find accounts across 3000+ platforms"},
        {"name": "Breach check",       "tool": "intel_breach",    "risk": "LOW",    "desc": "Breach database lookup"},
        {"name": "Dark web",           "tool": "intel_darkweb",   "risk": "LOW",    "desc": "Dark web and paste site search"},
        {"name": "Name OSINT",         "tool": "intel_name",      "risk": "LOW",    "desc": "Name-based web and social search"},
        {"name": "Report",             "tool": "generate_report", "risk": "LOW",    "desc": "Compile dossier"},
    ],
    "osint_org": [
        {"name": "WHOIS",              "tool": "whois",           "risk": "LOW",    "desc": "Domain registration data"},
        {"name": "DNS footprint",      "tool": "dig",             "risk": "LOW",    "desc": "DNS records and zone data"},
        {"name": "Subdomain enum",     "tool": "vm_subfinder",    "risk": "LOW",    "desc": "Passive subdomain discovery"},
        {"name": "Tech stack",         "tool": "http_fingerprint", "risk": "LOW",   "desc": "Web technology detection"},
        {"name": "Email harvest",      "tool": "vm_theharvester", "risk": "LOW",    "desc": "Employee emails"},
        {"name": "Shodan",             "tool": "intel_shodan",    "risk": "LOW",    "desc": "Exposed services"},
        {"name": "Breach check",       "tool": "intel_breach",    "risk": "LOW",    "desc": "Domain breach history"},
        {"name": "Report",             "tool": "generate_report", "risk": "LOW",    "desc": "Compile org footprint"},
    ],
}


# ── System prompt ──────────────────────────────────────────────────────────────

_PLANNER_SYSTEM = """You are T's autonomous planning engine.

Given the current task state, decide the SINGLE BEST next action.

Output EXACTLY one JSON object on one line:
NEXT_ACTION: {"tool": "<tool_name>", "params": {"key": "value"}, "step_name": "<short name>", "reason": "<one sentence why>"}

Or if the task is complete:
TASK_COMPLETE: {"summary": "<brief findings summary>"}

## RULES
- Choose tools from the AVAILABLE TOOLS list only
- Risk LOW/MEDIUM tools: run without asking — just output NEXT_ACTION
- Risk HIGH/CRITICAL tools: output NEXT_ACTION — executor will confirm with user
- Never repeat a step that already succeeded
- If a step failed, try an alternative approach
- If all reasonable steps exhausted → TASK_COMPLETE
- Keep step_name short (2-4 words)
- Keep reason to one sentence

## AVAILABLE TOOLS
{tools}

## CURRENT STATE
{context}
"""


async def next_step(
    memory: WorkingMemory,
    groq_key: str,
    available_tools: list[str],
) -> dict | None:
    """
    Ask the LLM what to do next given the current working memory.
    Returns a dict with tool/params/step_name/reason, or None if task is complete.
    """
    context = memory.to_context()
    tools_list = "\n".join(f"  - {t}" for t in available_tools)
    system = _PLANNER_SYSTEM.format(tools=tools_list, context=context)

    prompt = (
        f"Task: {memory.goal}\n"
        f"Target: {memory.target}\n\n"
        f"Based on the current state above, what is the single best next action?"
    )

    raw = await _llm_complete(system, prompt, groq_key)
    log.debug(f"planner raw: {raw[:200]}")

    # Parse TASK_COMPLETE
    complete_match = re.search(r"TASK_COMPLETE:\s*(\{.+\})", raw, re.DOTALL)
    if complete_match:
        try:
            return {"done": True, **json.loads(complete_match.group(1))}
        except Exception:
            return {"done": True, "summary": raw}

    # Parse NEXT_ACTION
    action_match = re.search(r"NEXT_ACTION:\s*(\{.+\})", raw, re.DOTALL)
    if action_match:
        try:
            action = json.loads(_clean_json(action_match.group(1)))
            action["done"] = False
            return action
        except Exception as e:
            log.warning(f"planner parse error: {e} — raw: {raw[:200]}")
            return None

    # Fallback — LLM didn't follow format
    return None


async def _llm_complete(system: str, prompt: str, groq_key: str) -> str:
    """Single non-streaming LLM call for planning."""
    from core.llm import _stream_groq, _ollama_online, _stream_ollama
    from core.llm import GROQ_MODEL_PRIMARY, OLLAMA_MODEL_DEFAULT

    messages = [{"role": "user", "content": prompt}]
    result   = ""

    try:
        if groq_key:
            async for chunk in _stream_groq(system, messages, groq_key, GROQ_MODEL_PRIMARY):
                result += chunk
            return result
        if await _ollama_online():
            async for chunk in _stream_ollama(system, messages, OLLAMA_MODEL_DEFAULT):
                result += chunk
            return result
    except Exception as e:
        log.warning(f"planner LLM error: {e}")

    return ""


def _clean_json(s: str) -> str:
    """Fix common LLM JSON formatting mistakes."""
    s = s.strip()
    # Remove trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)
    # Replace single quotes with double quotes (carefully)
    if "'" in s and '"' not in s:
        s = s.replace("'", '"')
    return s
