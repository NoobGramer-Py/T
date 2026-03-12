"""
Tool registry for T's agent system.
Each tool is a callable that takes a dict of params and returns a string result.
Tools run real commands via subprocess — output is fed back to the LLM.
"""

import asyncio
import subprocess
import shutil
from dataclasses import dataclass
from typing import Callable, Awaitable
from core.logger import get_logger

log = get_logger("agents.tools")


@dataclass
class Tool:
    name:        str
    description: str
    params:      dict[str, str]          # param_name → description
    fn:          Callable[..., Awaitable[str]]
    requires_confirmation: bool = False  # if True, agent must ask before running


# ─── Tool implementations ──────────────────────────────────────────────────────

async def _run(cmd: list[str], timeout: int = 30) -> str:
    """Run a subprocess and return stdout+stderr as a single string."""
    if not shutil.which(cmd[0]):
        return f"[ERROR] '{cmd[0]}' not found on PATH. Install it first."
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
        return f"[TIMEOUT] Command exceeded {timeout}s limit."
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


async def tool_curl(url: str, **_) -> str:
    return await _run(["curl", "-sI", "--max-time", "10", url], timeout=15)


async def tool_traceroute(target: str, **_) -> str:
    return await _run(["tracert", target], timeout=30)


async def tool_netstat(**_) -> str:
    return await _run(["netstat", "-ano"], timeout=10)


async def tool_powershell(command: str, **_) -> str:
    """Run a PowerShell command. Requires confirmation."""
    return await _run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        timeout=30,
    )


async def tool_python_script(code: str, **_) -> str:
    """Execute a Python snippet inline. Requires confirmation."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmpfile = f.name
    try:
        result = await _run(["python", tmpfile], timeout=30)
    finally:
        os.unlink(tmpfile)
    return result


# ─── Registry ──────────────────────────────────────────────────────────────────

TOOLS: dict[str, Tool] = {
    "nmap_quick": Tool(
        name="nmap_quick",
        description="Quick nmap scan (-sV --open -T4) on a target IP or hostname. Returns open ports and services.",
        params={"target": "IP address or hostname to scan"},
        fn=tool_nmap_quick,
    ),
    "nmap_full": Tool(
        name="nmap_full",
        description="Full nmap scan (-sV -sC -O -p-) on a target. Slow but thorough. OS detection included.",
        params={"target": "IP address or hostname to scan"},
        fn=tool_nmap_full,
        requires_confirmation=True,
    ),
    "ping": Tool(
        name="ping",
        description="Ping a target to check reachability.",
        params={"target": "IP or hostname", "count": "Number of pings (default 4)"},
        fn=tool_ping,
    ),
    "whois": Tool(
        name="whois",
        description="WHOIS lookup for a domain or IP.",
        params={"target": "Domain or IP"},
        fn=tool_whois,
    ),
    "dig": Tool(
        name="dig",
        description="DNS lookup for a domain.",
        params={"target": "Domain", "record_type": "Record type: A, MX, NS, TXT, CNAME (default A)"},
        fn=tool_dig,
    ),
    "curl_headers": Tool(
        name="curl_headers",
        description="Fetch HTTP headers from a URL to identify server, tech stack, security headers.",
        params={"url": "Full URL including scheme"},
        fn=tool_curl,
    ),
    "traceroute": Tool(
        name="traceroute",
        description="Trace the network path to a target.",
        params={"target": "IP or hostname"},
        fn=tool_traceroute,
    ),
    "netstat": Tool(
        name="netstat",
        description="Show all active network connections and listening ports on this machine.",
        params={},
        fn=tool_netstat,
    ),
    "powershell": Tool(
        name="powershell",
        description="Run a PowerShell command on Abdul's Windows machine. Use for system tasks.",
        params={"command": "PowerShell command string"},
        fn=tool_powershell,
        requires_confirmation=True,
    ),
    "python_script": Tool(
        name="python_script",
        description="Execute a Python script inline for data processing or automation.",
        params={"code": "Python code to execute"},
        fn=tool_python_script,
        requires_confirmation=True,
    ),
}


def get_tool(name: str) -> Tool | None:
    return TOOLS.get(name)


def tool_descriptions() -> str:
    """Format all tools for inclusion in the agent system prompt."""
    lines = []
    for t in TOOLS.values():
        params = ", ".join(f"{k}: {v}" for k, v in t.params.items()) or "none"
        conf   = " [REQUIRES CONFIRMATION]" if t.requires_confirmation else ""
        lines.append(f'- {t.name}{conf}: {t.description} | params: {params}')
    return "\n".join(lines)
