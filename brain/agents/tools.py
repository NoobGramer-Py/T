"""
Tool registry for T's agent system.
Each tool is a callable that takes a dict of params and returns a string result.
"""

import asyncio
import shutil
from dataclasses import dataclass
from typing import Callable, Awaitable
from core.logger import get_logger

log = get_logger("agents.tools")


@dataclass
class Tool:
    name:                  str
    description:           str
    params:                dict[str, str]
    fn:                    Callable[..., Awaitable[str]]
    requires_confirmation: bool = False


# ─── System tools ──────────────────────────────────────────────────────────────

async def _run(cmd: list[str], timeout: int = 30) -> str:
    if not shutil.which(cmd[0]):
        return f"[ERROR] '{cmd[0]}' not found on PATH."
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        return (out + ("\n[STDERR]\n" + err if err else "")).strip()
    except asyncio.TimeoutError:
        return f"[TIMEOUT] Command exceeded {timeout}s."
    except Exception as e:
        return f"[ERROR] {e}"


async def tool_nmap_quick(target: str, **_) -> str:
    return await _run(["nmap", "-sV", "--open", "-T4", target], timeout=60)

async def tool_nmap_full(target: str, **_) -> str:
    return await _run(["nmap", "-sV", "-sC", "-O", "--open", "-T4", "-p-", target], timeout=300)

async def tool_ping(target: str, count: str = "4", **_) -> str:
    return await _run(["ping", "-n", count, target], timeout=15)

async def tool_whois(target: str, **_) -> str:
    return await _run(["whois", target], timeout=15)

async def tool_dig(target: str, record_type: str = "A", **_) -> str:
    return await _run(["dig", target, record_type, "+short"], timeout=10)

async def tool_traceroute(target: str, **_) -> str:
    return await _run(["tracert", target], timeout=30)

async def tool_netstat(**_) -> str:
    return await _run(["netstat", "-ano"], timeout=10)

async def tool_powershell(command: str, **_) -> str:
    return await _run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        timeout=30,
    )

async def tool_python_script(code: str, **_) -> str:
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmpfile = f.name
    try:
        return await _run(["python", tmpfile], timeout=60)
    finally:
        os.unlink(tmpfile)


# ─── Web attack tools ──────────────────────────────────────────────────────────

async def tool_http_fingerprint(url: str, **_) -> str:
    from agents.web_attack import http_fingerprint
    return await http_fingerprint(url)

async def tool_find_login_form(url: str, **_) -> str:
    from agents.web_attack import find_login_form
    return await find_login_form(url)

async def tool_probe_login(
    url: str, username_field: str, password_field: str,
    username: str, password: str, extra_fields: str = "", **_
) -> str:
    from agents.web_attack import probe_login
    return await probe_login(url, username_field, password_field, username, password, extra_fields)

async def tool_sql_injection_login(
    url: str, username_field: str, password_field: str, **_
) -> str:
    from agents.web_attack import sql_injection_login
    return await sql_injection_login(url, username_field, password_field)

async def tool_directory_enum(base_url: str, wordlist: str = "common", **_) -> str:
    from agents.web_attack import directory_enum
    return await directory_enum(base_url, wordlist)

async def tool_fetch_page(url: str, cookies: str = "", **_) -> str:
    from agents.web_attack import fetch_page_with_cookies
    return await fetch_page_with_cookies(url, cookies)


# ─── Registry ──────────────────────────────────────────────────────────────────

TOOLS: dict[str, Tool] = {
    # ── Recon ──
    "nmap_quick": Tool(
        name="nmap_quick",
        description="Quick nmap scan (-sV --open -T4). Returns open ports and services.",
        params={"target": "IP or hostname"},
        fn=tool_nmap_quick,
    ),
    "nmap_full": Tool(
        name="nmap_full",
        description="Full nmap scan with OS detection, all ports. Slow but thorough.",
        params={"target": "IP or hostname"},
        fn=tool_nmap_full,
        requires_confirmation=True,
    ),
    "ping": Tool(
        name="ping",
        description="Check if target is reachable.",
        params={"target": "IP or hostname", "count": "ping count (default 4)"},
        fn=tool_ping,
    ),
    "whois": Tool(
        name="whois",
        description="WHOIS lookup for a domain or IP.",
        params={"target": "domain or IP"},
        fn=tool_whois,
    ),
    "dig": Tool(
        name="dig",
        description="DNS lookup.",
        params={"target": "domain", "record_type": "A/MX/NS/TXT/CNAME (default A)"},
        fn=tool_dig,
    ),
    "traceroute": Tool(
        name="traceroute",
        description="Trace network path to target.",
        params={"target": "IP or hostname"},
        fn=tool_traceroute,
    ),
    "netstat": Tool(
        name="netstat",
        description="Show active connections and listening ports on this machine.",
        params={},
        fn=tool_netstat,
    ),

    # ── Web attack ──
    "http_fingerprint": Tool(
        name="http_fingerprint",
        description="Full HTTP fingerprint: server, tech stack, security headers, cookies, body preview. Always run this first on a web target.",
        params={"url": "full URL including scheme"},
        fn=tool_http_fingerprint,
    ),
    "find_login_form": Tool(
        name="find_login_form",
        description="Fetch a page and extract all forms: action URL, method, field names, hidden fields (CSRF tokens). Run before any login attack.",
        params={"url": "page URL containing the login form"},
        fn=tool_find_login_form,
    ),
    "probe_login": Tool(
        name="probe_login",
        description="Submit a single login attempt and analyze the response for success/failure indicators, redirects, and cookies.",
        params={
            "url":            "form action URL",
            "username_field": "name attribute of the username input",
            "password_field": "name attribute of the password input",
            "username":       "username to try",
            "password":       "password to try",
            "extra_fields":   "JSON of additional fields e.g. CSRF token: {\"_token\": \"abc\"}",
        },
        fn=tool_probe_login,
    ),
    "sql_injection_login": Tool(
        name="sql_injection_login",
        description="Test login form for SQL injection bypass. Tries 12 classic payloads. Returns which payload (if any) bypassed authentication.",
        params={
            "url":            "form action URL",
            "username_field": "name of username input field",
            "password_field": "name of password input field",
        },
        fn=tool_sql_injection_login,
    ),
    "directory_enum": Tool(
        name="directory_enum",
        description="Enumerate common paths on a web server. wordlist=common (default) or admin (admin-focused).",
        params={"base_url": "base URL e.g. http://target.com", "wordlist": "common or admin"},
        fn=tool_directory_enum,
    ),
    "fetch_page": Tool(
        name="fetch_page",
        description="Fetch a page with optional cookies. Use to verify session after login or access protected pages.",
        params={"url": "URL to fetch", "cookies": "JSON string of cookies e.g. {\"session\": \"abc\"}"},
        fn=tool_fetch_page,
    ),

    # ── System ──
    "powershell": Tool(
        name="powershell",
        description="Run a PowerShell command on Abdul's Windows machine.",
        params={"command": "PowerShell command"},
        fn=tool_powershell,
        requires_confirmation=True,
    ),
    "python_script": Tool(
        name="python_script",
        description="Execute a Python script. Use for custom attack logic, data parsing, or automation not covered by other tools.",
        params={"code": "Python code to execute"},
        fn=tool_python_script,
        requires_confirmation=True,
    ),
}


def get_tool(name: str) -> Tool | None:
    return TOOLS.get(name)


def tool_descriptions() -> str:
    lines = []
    for t in TOOLS.values():
        params = ", ".join(f"{k}: {v}" for k, v in t.params.items()) or "none"
        conf   = " [REQUIRES CONFIRMATION]" if t.requires_confirmation else ""
        lines.append(f"- {t.name}{conf}: {t.description} | params: {params}")
    return "\n".join(lines)
