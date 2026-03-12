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

async def tool_wordpress_user_enum(base_url: str, **_) -> str:
    from agents.web_attack import wordpress_user_enum
    return await wordpress_user_enum(base_url)

async def tool_wp_full_attack(target_url: str, **_) -> str:
    from agents.wp_attack import full_attack
    return await full_attack(target_url)

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


# ─── Integration tools — Web ───────────────────────────────────────────────────

async def tool_web_search(query: str, **_) -> str:
    from integrations.web import web_search
    return await web_search(query)

async def tool_get_weather(location: str, **_) -> str:
    from integrations.web import get_weather
    return await get_weather(location)

async def tool_fetch_url(url: str, **_) -> str:
    from integrations.web import fetch_url
    return await fetch_url(url)

async def tool_get_news(topic: str = "", **_) -> str:
    from integrations.web import get_news
    return await get_news(topic)


# ─── Integration tools — System ───────────────────────────────────────────────

async def tool_launch_app(name: str, **_) -> str:
    from integrations.system_control import launch_app
    return await launch_app(name)

async def tool_open_url(url: str, browser: str = "", **_) -> str:
    from integrations.system_control import open_url
    return await open_url(url, browser)

async def tool_get_clipboard(**_) -> str:
    from integrations.system_control import get_clipboard
    return await get_clipboard()

async def tool_set_clipboard(content: str, **_) -> str:
    from integrations.system_control import set_clipboard
    return await set_clipboard(content)

async def tool_search_files(query: str, path: str = "", extension: str = "", **_) -> str:
    from integrations.system_control import search_files
    return await search_files(query, path, extension)

async def tool_read_file(path: str, **_) -> str:
    from integrations.system_control import read_file
    return await read_file(path)

async def tool_write_file(path: str, content: str, **_) -> str:
    from integrations.system_control import write_file
    return await write_file(path, content)

async def tool_list_directory(path: str = "~", **_) -> str:
    from integrations.system_control import list_directory
    return await list_directory(path)

async def tool_get_processes(filter_name: str = "", **_) -> str:
    from integrations.system_control import get_running_processes
    return await get_running_processes(filter_name)

async def tool_kill_process(name_or_pid: str, **_) -> str:
    from integrations.system_control import kill_process
    return await kill_process(name_or_pid)

async def tool_screenshot(save_path: str = "", **_) -> str:
    from integrations.system_control import take_screenshot
    return await take_screenshot(save_path)

async def tool_system_info(**_) -> str:
    from integrations.system_control import get_system_info
    return await get_system_info()



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
    "wp_full_attack": Tool(
        name="wp_full_attack",
        description="Full automated WordPress attack chain in one shot: fingerprint → username enumeration → plugin CVE detection → SQLi test → XML-RPC brute force with contextual wordlist → wp-login.php brute force. Uses site domain, emails, and usernames found to generate targeted passwords. Returns credentials if found, or honest failure report.",
        params={"target_url": "WordPress site URL or wp-login.php URL"},
        fn=tool_wp_full_attack,
        requires_confirmation=True,
    ),
    "wordpress_user_enum": Tool(
        name="wordpress_user_enum",
        description="WordPress-specific: enumerate valid usernames via REST API, author archives, and login error messages. Run this before brute forcing a WordPress login — valid usernames make attacks far more efficient.",
        params={"base_url": "WordPress site base URL or wp-login.php URL"},
        fn=tool_wordpress_user_enum,
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

    # ── Web intelligence ──
    "web_search": Tool(
        name="web_search",
        description="Search the web via DuckDuckGo. Use for current events, research, CVEs, documentation, anything requiring live web data.",
        params={"query": "search query"},
        fn=tool_web_search,
    ),
    "get_weather": Tool(
        name="get_weather",
        description="Get current weather and 3-day forecast for any city or location.",
        params={"location": "city name or location e.g. Lahore, London, New York"},
        fn=tool_get_weather,
    ),
    "fetch_url": Tool(
        name="fetch_url",
        description="Fetch and read the text content of any URL. Use to read articles, docs, pages, API responses.",
        params={"url": "full URL to fetch"},
        fn=tool_fetch_url,
    ),
    "get_news": Tool(
        name="get_news",
        description="Get latest news headlines, optionally filtered by topic.",
        params={"topic": "news topic or keyword (empty for top headlines)"},
        fn=tool_get_news,
    ),

    # ── System control ──
    "launch_app": Tool(
        name="launch_app",
        description="Launch an application by name. Supports: chrome, firefox, edge, vscode, notepad, terminal, calculator, explorer, spotify, discord, wireshark, burpsuite, vlc, obs, and more.",
        params={"name": "application name"},
        fn=tool_launch_app,
    ),
    "open_url": Tool(
        name="open_url",
        description="Open a URL in the browser.",
        params={"url": "URL to open", "browser": "chrome/firefox/edge (optional, uses default if empty)"},
        fn=tool_open_url,
    ),
    "get_clipboard": Tool(
        name="get_clipboard",
        description="Read the current clipboard content.",
        params={},
        fn=tool_get_clipboard,
    ),
    "set_clipboard": Tool(
        name="set_clipboard",
        description="Write text to the clipboard.",
        params={"content": "text to put on clipboard"},
        fn=tool_set_clipboard,
    ),
    "search_files": Tool(
        name="search_files",
        description="Search for files by name on the filesystem.",
        params={
            "query":     "filename or partial name to search",
            "path":      "root directory to search (default: home folder)",
            "extension": "filter by extension e.g. .pdf .py .txt (optional)",
        },
        fn=tool_search_files,
    ),
    "read_file": Tool(
        name="read_file",
        description="Read the contents of a file.",
        params={"path": "full file path"},
        fn=tool_read_file,
    ),
    "write_file": Tool(
        name="write_file",
        description="Write text content to a file. Creates directories as needed.",
        params={"path": "full file path", "content": "text content to write"},
        fn=tool_write_file,
        requires_confirmation=True,
    ),
    "list_directory": Tool(
        name="list_directory",
        description="List files and folders in a directory.",
        params={"path": "directory path (default: home folder)"},
        fn=tool_list_directory,
    ),
    "get_processes": Tool(
        name="get_processes",
        description="List running processes, sorted by CPU usage. Optionally filter by name.",
        params={"filter_name": "process name filter (optional)"},
        fn=tool_get_processes,
    ),
    "kill_process": Tool(
        name="kill_process",
        description="Kill a running process by name or PID.",
        params={"name_or_pid": "process name or numeric PID"},
        fn=tool_kill_process,
        requires_confirmation=True,
    ),
    "screenshot": Tool(
        name="screenshot",
        description="Take a screenshot of the screen and save it.",
        params={"save_path": "file path to save PNG (optional, defaults to ~/Screenshots/)"},
        fn=tool_screenshot,
    ),
    "system_info": Tool(
        name="system_info",
        description="Get detailed system info: OS, CPU, RAM, uptime, username, IP address.",
        params={},
        fn=tool_system_info,
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
