"""
Network pivot module for T's red team lab.
Discovers devices on the network and maps their attack surface.
"""

import asyncio
import re
from typing import AsyncIterator, TYPE_CHECKING
from offensive.vm_bridge import vm
from offensive.stream import stream_subprocess
from .session_log import get_session
from core.logger import get_logger

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("lab.pivot")

# TTL hints for OS detection
_TTL_OS = {
    range(60, 65):  "Linux/Android",
    range(126, 129):"Windows",
    range(252, 256):"Network device / router",
}


def _guess_os(ttl: int) -> str:
    for r, os_name in _TTL_OS.items():
        if ttl in r:
            return os_name
    return "Unknown"


async def arp_scan(subnet: str) -> AsyncIterator[dict]:
    """
    Fast ARP scan of the subnet.
    Yields device dicts as they are found.
    """
    cmd = f"sudo arp-scan --localnet --interface=eth0 2>/dev/null || arp-scan {subnet} 2>/dev/null"
    async for line in vm.run(cmd, timeout=60):
        # arp-scan output: "192.168.1.5  aa:bb:cc:dd:ee:ff  Vendor"
        parts = line.split("\t")
        if len(parts) >= 2 and re.match(r"\d+\.\d+\.\d+\.\d+", parts[0]):
            ip  = parts[0].strip()
            mac = parts[1].strip() if len(parts) > 1 else ""
            vendor = parts[2].strip() if len(parts) > 2 else ""
            yield {"ip": ip, "mac": mac, "vendor": vendor}


async def nmap_device(ip: str) -> dict:
    """
    Quick nmap of a single device — OS hint, top ports, services.
    Returns structured result dict.
    """
    result = {"ip": ip, "open_ports": [], "os_hint": "", "hostname": "", "services": []}
    cmd = f"nmap -sV -T4 --open -F -O --osscan-guess {ip} 2>/dev/null"
    output = []
    async for line in vm.run(cmd, timeout=60):
        output.append(line)
        # Parse open ports
        m = re.match(r"(\d+)/tcp\s+open\s+(\S+)\s*(.*)", line)
        if m:
            port = int(m.group(1))
            svc  = m.group(2)
            ver  = m.group(3).strip()
            result["open_ports"].append(port)
            result["services"].append({"port": port, "service": svc, "version": ver})
        # OS guess
        if "OS details:" in line or "Running:" in line:
            result["os_hint"] = line.split(":", 1)[-1].strip()
        if "Nmap scan report for" in line:
            m2 = re.search(r"for (.+) \(", line)
            if m2:
                result["hostname"] = m2.group(1)

    return result


def classify_device(device: dict) -> str:
    """Guess device type from open ports + OS + vendor."""
    ports = set(device.get("open_ports", []))
    os    = device.get("os_hint", "").lower()
    vendor= device.get("vendor", "").lower()

    if 5555 in ports or "android" in os:
        return "android"
    if 62078 in ports or "apple" in vendor or "ios" in os:
        return "ios"
    if {80, 443, 8080}.intersection(ports) and any(r in vendor for r in ["tp-link","netgear","asus","linksys","d-link","tplink","huawei","zte"]):
        return "router"
    if {139, 445, 3389}.intersection(ports) or "windows" in os:
        return "windows"
    if {22}.issubset(ports) and "linux" in os:
        return "linux"
    if {1883, 8883}.intersection(ports):
        return "iot_mqtt"
    if {554}.intersection(ports):
        return "camera"
    return "unknown"


async def full_network_scan(client: "Client", subnet: str) -> None:
    """
    Full network discovery pipeline.
    Sends lab_device_found events as each device is identified.
    """
    session = get_session()
    session.record("recon", "arp_scan", f"Scanning {subnet}")

    found_ips: list[str] = []

    # Phase 1 — ARP scan (fast, gets MAC + vendor)
    await client.send({"type": "lab_step_update", "step": "recon",
                       "status": "running", "message": f"ARP scanning {subnet}..."})

    async for dev in arp_scan(subnet):
        ip = dev["ip"]
        if ip not in found_ips:
            found_ips.append(ip)
            await client.send({
                "type":    "lab_device_found",
                "ip":      ip,
                "mac":     dev["mac"],
                "vendor":  dev["vendor"],
                "phase":   "arp",
            })

    # Phase 2 — nmap each found device
    await client.send({"type": "lab_step_update", "step": "recon",
                       "status": "running", "message": f"Fingerprinting {len(found_ips)} devices..."})

    for ip in found_ips:
        detail = await nmap_device(ip)
        device_type = classify_device({**detail, "vendor": ""})
        session.add_device(
            ip=ip, mac="", hostname=detail["hostname"],
            os_hint=detail["os_hint"], open_ports=detail["open_ports"],
            device_type=device_type,
        )
        await client.send({
            "type":        "lab_device_found",
            "ip":          ip,
            "hostname":    detail["hostname"],
            "os_hint":     detail["os_hint"],
            "open_ports":  detail["open_ports"],
            "services":    detail["services"],
            "device_type": device_type,
            "phase":       "nmap",
        })

        # Flag high-value targets
        if device_type == "router":
            session.record("recon", "device_found", f"Router at {ip}", "high")
        elif device_type == "android":
            session.record("recon", "device_found", f"Android device at {ip}", "high")
        elif device_type == "windows":
            session.record("recon", "device_found", f"Windows host at {ip}", "high")

    await client.send({"type": "lab_step_update", "step": "recon",
                       "status": "done",
                       "message": f"Found {len(found_ips)} devices.",
                       "count": len(found_ips)})
