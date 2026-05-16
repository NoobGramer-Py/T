"""
Attack Detector for T.
Monitors system logs and network connections for attack indicators.
On detection: alerts T, identifies the attacker, collects evidence for reporting.
Does NOT launch counter-attacks — collects evidence for legal reporting only.
"""

import asyncio
import re
import time
from typing import AsyncIterator, TYPE_CHECKING
from core.logger import get_logger

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("guardian.attack_detector")

# Active monitoring tasks
_monitor_tasks: dict[str, asyncio.Task] = {}


# ── Attack signatures ──────────────────────────────────────────────────────────

ATTACK_PATTERNS = [
    # Brute force SSH
    (r"Failed password for .+ from (\d+\.\d+\.\d+\.\d+)",    "SSH_BRUTE_FORCE",  "HIGH"),
    (r"Invalid user .+ from (\d+\.\d+\.\d+\.\d+)",            "SSH_USER_ENUM",    "MEDIUM"),
    # Port scanning
    (r"SYN_RECV.*(\d+\.\d+\.\d+\.\d+)",                       "PORT_SCAN",        "MEDIUM"),
    # Web attacks
    (r"(\d+\.\d+\.\d+\.\d+).*(?:\.\.\/|%2e%2e|union.*select|<script)", "WEB_ATTACK", "HIGH"),
    # Suspicious connections
    (r"ESTABLISHED.*:(\d+\.\d+\.\d+\.\d+):\d+",               "ACTIVE_CONNECTION","LOW"),
]


# ── Log monitoring ─────────────────────────────────────────────────────────────

async def monitor_logs(
    client: "Client",
    session_id: str,
    log_file: str = "/var/log/auth.log",
) -> None:
    """
    Monitor a log file for attack patterns in real time.
    Sends alerts to T UI when attacks are detected.
    """
    stop_key = f"_stop_monitor_{session_id}"
    log.info(f"Starting log monitor: {log_file}")

    await client.send({
        "type":       "guardian_started",
        "session_id": session_id,
        "message":    f"Monitoring {log_file} for attacks...",
    })

    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            "tail", "-F", "-n", "0", log_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        while not getattr(client, stop_key, False):
            try:
                line_bytes = await asyncio.wait_for(
                    proc.stdout.readline(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue

            if not line_bytes:
                break

            line = line_bytes.decode(errors="replace").strip()
            if not line:
                continue

            # Check against attack patterns
            for pattern, attack_type, severity in ATTACK_PATTERNS:
                m = re.search(pattern, line, re.IGNORECASE)
                if m:
                    attacker_ip = m.group(1) if m.lastindex else "unknown"
                    await client.send({
                        "type":        "guardian_alert",
                        "session_id":  session_id,
                        "attack_type": attack_type,
                        "severity":    severity,
                        "attacker_ip": attacker_ip,
                        "log_line":    line,
                        "timestamp":   int(time.time()),
                    })
                    log.warning(f"Attack detected: {attack_type} from {attacker_ip}")
                    break

    except FileNotFoundError:
        await client.send({
            "type":    "guardian_error",
            "message": f"Log file not found: {log_file}",
        })
    except Exception as e:
        await client.send({
            "type":    "guardian_error",
            "message": str(e),
        })
    finally:
        if proc and proc.returncode is None:
            proc.terminate()
        log.info(f"Log monitor stopped: {log_file}")
        await client.send({"type": "guardian_stopped", "session_id": session_id})


async def monitor_connections(
    client: "Client",
    session_id: str,
    interval: int = 10,
) -> None:
    """
    Periodically check active network connections for suspicious activity.
    Alerts on new connections from unknown IPs.
    """
    stop_key    = f"_stop_monitor_{session_id}"
    known_conns: set[str] = set()

    await client.send({
        "type":       "guardian_started",
        "session_id": session_id,
        "message":    "Monitoring network connections...",
    })

    while not getattr(client, stop_key, False):
        try:
            import psutil
            current: set[str] = set()

            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "ESTABLISHED" and conn.raddr:
                    key = f"{conn.raddr.ip}:{conn.raddr.port}"
                    current.add(key)

                    if key not in known_conns:
                        # New connection — check if suspicious
                        ip = conn.raddr.ip
                        if not _is_local_ip(ip):
                            await client.send({
                                "type":        "guardian_alert",
                                "session_id":  session_id,
                                "attack_type": "NEW_CONNECTION",
                                "severity":    "LOW",
                                "attacker_ip": ip,
                                "log_line":    f"New connection: {key} (PID {conn.pid})",
                                "timestamp":   int(time.time()),
                            })

            known_conns = current

        except Exception as e:
            log.warning(f"Connection monitor error: {e}")

        await asyncio.sleep(interval)

    await client.send({"type": "guardian_stopped", "session_id": session_id})


def _is_local_ip(ip: str) -> bool:
    return (ip.startswith("192.168.") or ip.startswith("10.") or
            ip.startswith("172.16.") or ip.startswith("127.") or
            ip == "::1")


async def stop_monitor(client: "Client", session_id: str) -> None:
    setattr(client, f"_stop_monitor_{session_id}", True)
    task = _monitor_tasks.pop(session_id, None)
    if task:
        task.cancel()


# ── Attacker OSINT — evidence collection ──────────────────────────────────────

async def investigate_attacker(ip: str) -> AsyncIterator[str]:
    """
    Collect OSINT on an attacker IP for legal reporting.
    Gathers: geolocation, ISP, abuse reports, reverse DNS, open ports.
    This is evidence collection — NOT a counter-attack.
    """
    yield f"[T] Attacker Investigation: {ip}"
    yield "═" * 60
    yield "Collecting evidence for legal reporting..."
    yield ""

    # Stage 1: Geolocation and ISP
    yield "[1/5] Geolocation and ISP..."
    from offensive.vm_bridge import vm
    cmd1 = (
        f"curl -sL --connect-timeout 10 'https://ipapi.co/{ip}/json/' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,json; d=json.load(sys.stdin); "
        f"fields=['ip','city','region','country_name','org','isp','timezone','latitude','longitude']; "
        f"[print(f'{{k}}: {{d.get(k,\\'N/A\\')}}') for k in fields]\""
        f" 2>/dev/null"
    )
    async for line in vm.run(cmd1, timeout=15):
        yield f"  {line}"

    # Stage 2: Abuse reports
    yield "\n[2/5] Known abuse reports (AbuseIPDB)..."
    cmd2 = (
        f"curl -sL --connect-timeout 10 "
        f"-H 'Key: ' -H 'Accept: application/json' "
        f"'https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90&verbose' "
        f"2>/dev/null | "
        f"python3 -c \""
        f"import sys,json; d=json.load(sys.stdin).get('data',{{}}); "
        f"print(f'Abuse score: {{d.get(\\\"abuseConfidenceScore\\\",0)}}%'); "
        f"print(f'Total reports: {{d.get(\\\"totalReports\\\",0)}}'); "
        f"print(f'Last reported: {{d.get(\\\"lastReportedAt\\\",\\\"Never\\\")}}'); "
        f"print(f'ISP: {{d.get(\\\"isp\\\",\\\"Unknown\\\")}}'); "
        f"print(f'Usage type: {{d.get(\\\"usageType\\\",\\\"Unknown\\\")}}')"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(cmd2, timeout=15):
        yield f"  {line}"

    # Stage 3: Reverse DNS
    yield "\n[3/5] Reverse DNS lookup..."
    cmd3 = f"dig -x {ip} +short 2>/dev/null; host {ip} 2>/dev/null | head -3"
    async for line in vm.run(cmd3, timeout=10):
        yield f"  {line}"

    # Stage 4: WHOIS — who owns this IP
    yield "\n[4/5] WHOIS — IP owner and abuse contact..."
    cmd4 = (
        f"whois {ip} 2>/dev/null | "
        f"grep -iE 'netname|orgname|country|abuse|mntner|descr|cidr|inetnum' | "
        f"sort -u | head -15"
    )
    async for line in vm.run(cmd4, timeout=15):
        yield f"  {line}"

    # Stage 5: Shodan quick check
    yield "\n[5/5] Shodan — known services on this IP..."
    cmd5 = (
        f"curl -sL --connect-timeout 10 "
        f"'https://internetdb.shodan.io/{ip}' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,json; d=json.load(sys.stdin); "
        f"print(f'Open ports: {{d.get(\\\"ports\\\",[])}}'  ); "
        f"print(f'Tags: {{d.get(\\\"tags\\\",[])}}'); "
        f"print(f'Vulns: {{d.get(\\\"vulns\\\",[])}}'); "
        f"print(f'Hostnames: {{d.get(\\\"hostnames\\\",[])}}')"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(cmd5, timeout=15):
        yield f"  {line}"

    # Report generation
    yield "\n" + "═" * 60
    yield "[T] EVIDENCE SUMMARY"
    yield f"  Attacker IP: {ip}"
    yield f"  Timestamp:   {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"
    yield ""
    yield "REPORTING RESOURCES:"
    yield f"  AbuseIPDB:   https://www.abuseipdb.com/report?ip={ip}"
    yield f"  Spamhaus:    https://www.spamhaus.org/query/ip/{ip}"
    yield f"  PakCERT:     https://www.pakcert.org/report (Pakistan)"
    yield f"  NCERT:       https://www.ncert.gov.pk (Pakistan national CERT)"
    yield f"  FBI IC3:     https://www.ic3.gov (US)"
    yield f"  Europol:     https://www.europol.europa.eu/report-a-crime"
    yield ""
    yield "Save this output as evidence before reporting."
    yield "═" * 60


async def block_ip_local(ip: str) -> AsyncIterator[str]:
    """
    Block an attacker IP using the local firewall.
    Uses Windows Firewall on Windows, iptables on Linux.
    This is DEFENSIVE — drops inbound connections from the attacker.
    """
    yield f"[T] Blocking attacker IP: {ip}"
    yield "This is a defensive block — drops their connections to your machine."
    yield ""

    import sys
    if sys.platform == "win32":
        import subprocess
        rule_name = f"T-Block-{ip}"
        result = subprocess.run([
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={rule_name}",
            "dir=in", "action=block",
            f"remoteip={ip}",
            "protocol=any",
        ], capture_output=True, text=True)
        if result.returncode == 0:
            yield f"  ✓ Firewall rule added: {rule_name}"
            yield f"  ✓ All inbound traffic from {ip} is now blocked"
        else:
            yield f"  ✗ Failed: {result.stderr.strip()}"
            yield "  Tip: Run T as Administrator to modify firewall rules"
    else:
        from offensive.vm_bridge import vm
        cmd = f"sudo iptables -A INPUT -s {ip} -j DROP && echo BLOCKED"
        async for line in vm.run(cmd, timeout=10):
            yield f"  {line}"

    yield ""
    yield f"To unblock: remove firewall rule for {ip}"
