"""
System control integration for T.
Handles: app launch, browser control, file search, clipboard, process management.
Runs on Windows via PowerShell and subprocess — no additional tools required.
"""

import asyncio
import subprocess
import os
import re
from pathlib import Path
from core.logger import get_logger

log = get_logger("integrations.system")


async def _ps(command: str, timeout: int = 15) -> str:
    """Run a PowerShell command and return output."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-NoProfile", "-NonInteractive", "-Command", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        if err and not out:
            return f"[STDERR] {err}"
        return out or "[OK] Command executed."
    except asyncio.TimeoutError:
        return f"[TIMEOUT] Exceeded {timeout}s."
    except Exception as e:
        return f"[ERROR] {e}"


async def launch_app(name: str) -> str:
    """
    Launch an application by name or executable.
    Handles common apps by name (chrome, vscode, notepad, etc.).
    """
    aliases = {
        "chrome":        "chrome",
        "google chrome": "chrome",
        "firefox":       "firefox",
        "edge":          "msedge",
        "notepad":       "notepad",
        "notepad++":     "notepad++",
        "vscode":        "code",
        "vs code":       "code",
        "visual studio code": "code",
        "terminal":      "wt",
        "powershell":    "powershell",
        "cmd":           "cmd",
        "explorer":      "explorer",
        "file explorer": "explorer",
        "calculator":    "calc",
        "task manager":  "taskmgr",
        "paint":         "mspaint",
        "spotify":       "spotify",
        "discord":       "discord",
        "steam":         "steam",
        "obs":           "obs64",
        "vlc":           "vlc",
        "burpsuite":     "burpsuite",
        "wireshark":     "wireshark",
    }

    exe = aliases.get(name.lower().strip(), name)
    try:
        subprocess.Popen(
            [exe],
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return f"Launched: {name}"
    except Exception as e:
        return f"[ERROR] Could not launch {name!r}: {e}"


async def open_url(url: str, browser: str = "") -> str:
    """Open a URL in the default or specified browser."""
    if not url.startswith("http"):
        url = "https://" + url

    if browser:
        browser_map = {
            "chrome": "chrome",
            "firefox": "firefox",
            "edge": "msedge",
        }
        exe = browser_map.get(browser.lower(), browser)
        try:
            subprocess.Popen(
                [exe, url],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"Opened {url} in {browser}"
        except Exception as e:
            return f"[ERROR] {e}"

    # Default browser via PowerShell
    result = await _ps(f'Start-Process "{url}"')
    return f"Opened: {url}"


async def get_clipboard() -> str:
    """Read current clipboard content."""
    result = await _ps("Get-Clipboard")
    if not result or result.startswith("["):
        return "Clipboard is empty."
    return f"Clipboard: {result[:500]}"


async def set_clipboard(content: str) -> str:
    """Write text to clipboard."""
    safe = content.replace("'", "''")
    result = await _ps(f"Set-Clipboard -Value '{safe}'")
    return f"Clipboard set: {content[:80]}{'...' if len(content) > 80 else ''}"


async def search_files(query: str, path: str = "", extension: str = "") -> str:
    """
    Search for files by name on the system.
    path: search root (default: user home + common locations)
    extension: filter by extension e.g. .pdf .py .txt
    """
    root = path or str(Path.home())
    ext_filter = f"-Filter '*{extension}'" if extension else ""
    name_filter = f"*{query}*"

    cmd = (
        f"Get-ChildItem -Path '{root}' -Recurse -ErrorAction SilentlyContinue "
        f"-Filter '{name_filter}' {ext_filter} | "
        f"Select-Object -First 20 FullName, Length, LastWriteTime | "
        f"Format-Table -AutoSize | Out-String"
    )
    result = await _ps(cmd, timeout=30)
    if not result.strip() or result.startswith("["):
        return f"No files matching '{query}' found under {root}"
    return f"Files matching '{query}':\n{result}"


async def read_file(path: str, max_chars: int = 4000) -> str:
    """Read contents of a file."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"[ERROR] File not found: {path}"
        if p.stat().st_size > 5 * 1024 * 1024:
            return f"[ERROR] File too large (>{5}MB): {path}"
        text = p.read_text(encoding="utf-8", errors="replace")
        truncated = len(text) > max_chars
        return text[:max_chars] + (f"\n\n[truncated — {len(text)} total chars]" if truncated else "")
    except Exception as e:
        return f"[ERROR] {e}"


async def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written: {path} ({len(content)} chars)"
    except Exception as e:
        return f"[ERROR] {e}"


async def list_directory(path: str = "~") -> str:
    """List directory contents."""
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"[ERROR] Path not found: {path}"
        entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        lines = []
        for entry in entries[:50]:
            kind = "DIR " if entry.is_dir() else "FILE"
            size = f"{entry.stat().st_size:>10,} bytes" if entry.is_file() else ""
            lines.append(f"  [{kind}] {entry.name}  {size}")
        result = "\n".join(lines)
        if len(entries) > 50:
            result += f"\n  ... and {len(entries) - 50} more"
        return f"Directory: {p}\n\n{result}"
    except Exception as e:
        return f"[ERROR] {e}"


async def get_running_processes(filter_name: str = "") -> str:
    """List running processes, optionally filtered by name."""
    cmd = "Get-Process | Sort-Object CPU -Descending | Select-Object -First 30 Name, Id, CPU, WorkingSet | Format-Table -AutoSize | Out-String"
    if filter_name:
        cmd = f"Get-Process -Name '*{filter_name}*' -ErrorAction SilentlyContinue | Format-Table Name, Id, CPU, WorkingSet -AutoSize | Out-String"
    return await _ps(cmd)


async def kill_process(name_or_pid: str) -> str:
    """Kill a process by name or PID."""
    if name_or_pid.isdigit():
        cmd = f"Stop-Process -Id {name_or_pid} -Force"
    else:
        cmd = f"Stop-Process -Name '{name_or_pid}' -Force -ErrorAction SilentlyContinue"
    return await _ps(cmd)


async def take_screenshot(save_path: str = "") -> str:
    """Take a screenshot and save it."""
    if not save_path:
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = str(Path.home() / "Screenshots" / f"screenshot_{ts}.png")

    safe_path = save_path.replace("\\", "\\\\")
    cmd = (
        f"Add-Type -AssemblyName System.Windows.Forms; "
        f"$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
        f"$bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height; "
        f"$graphics = [System.Drawing.Graphics]::FromImage($bitmap); "
        f"$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size); "
        f"$bitmap.Save('{safe_path}'); "
        f"'Screenshot saved: {safe_path}'"
    )
    result = await _ps(cmd, timeout=10)
    return result


async def get_system_info() -> str:
    """Get detailed system information."""
    cmd = (
        "$os = Get-CimInstance Win32_OperatingSystem; "
        "$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1; "
        "$mem = [math]::Round($os.TotalVisibleMemorySize/1MB, 1); "
        "$free = [math]::Round($os.FreePhysicalMemory/1MB, 1); "
        "$uptime = (Get-Date) - $os.LastBootUpTime; "
        "\"OS: $($os.Caption) $($os.Version)\"; "
        "\"CPU: $($cpu.Name)\"; "
        "\"RAM: ${free}GB free / ${mem}GB total\"; "
        "\"Uptime: $([math]::Floor($uptime.TotalHours))h $($uptime.Minutes)m\"; "
        "\"User: $env:USERNAME on $env:COMPUTERNAME\"; "
        "\"IP: $((Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike '*Loopback*'} | Select-Object -First 1).IPAddress)\""
    )
    return await _ps(cmd)
