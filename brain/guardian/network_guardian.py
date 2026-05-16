"""
Network Guardian — scans home/friend networks, reports exposed devices
and vulnerabilities in plain language anyone can understand.
"""

import asyncio
import re
import subprocess
from typing import AsyncIterator
from offensive.vm_bridge import vm
from core.logger import get_logger

log = get_logger("guardian.network_guardian")


# Risk descriptions in plain language
RISK_PLAIN = {
    22:   ("SSH",         "Remote login port — ensure only trusted users have access"),
    23:   ("Telnet",      "INSECURE remote login — disable immediately, use SSH instead"),
    80:   ("HTTP",        "Web server without encryption — data visible to anyone on network"),
    443:  ("HTTPS",       "Secure web server — generally safe"),
    445:  ("SMB",         "Windows file sharing — high risk if exposed to internet"),
    3389: ("RDP",         "Windows Remote Desktop — common attack target, restrict access"),
    8080: ("HTTP-alt",    "Alternative web port — check if intentional"),
    8443: ("HTTPS-alt",   "Alternative secure web port"),
    21:   ("FTP",         "File transfer — INSECURE, use SFTP instead"),
    3306: ("MySQL",       "Database port — should NEVER be exposed to internet"),
    5432: ("PostgreSQL",  "Database port — should NEVER be exposed to internet"),
    6379: ("Redis",       "Cache server — often misconfigured, restrict access"),
    27017:("MongoDB",     "Database — check if authentication is enabled"),
    1433: ("SQL Server",  "Microsoft database — restrict to local network only"),
    5900: ("VNC",         "Remote desktop — ensure strong password is set"),
    554:  ("RTSP",        "Camera stream — ensure authentication is required"),
    9200: ("Elasticsearch","Search database — often left open without auth"),
}


async def scan_network(network: str = "") -> AsyncIterator[str]:
    """
    Scan a home network and report all devices with risk assessment.
    network: e.g. '192.168.1.0/24' — auto-detects if empty
    """
    yield "[T] Home Network Guardian Scan"
    yield "─" * 60
    yield "Scanning your network for all connected devices..."

    if not network:
        # Auto-detect local network
        cmd_detect = (
            "ip route | grep 'src' | awk '{print $1}' | head -3 2>/dev/null || "
            "route -n | grep 'UG' | awk '{print $1}' | head -3 2>/dev/null"
        )
        async for line in vm.run(cmd_detect, timeout=5):
            if "/" in line:
                network = line.strip()
                break

    if not network:
        network = "192.168.1.0/24"

    yield f"Network: {network}"
    yield ""

    # Quick discovery
    cmd_disc = (
        f"nmap -sn {network} 2>/dev/null | "
        f"grep -E 'report for|MAC' | "
        f"paste - - 2>/dev/null"
    )
    hosts_found = []
    async for line in vm.run(cmd_disc, timeout=60):
        m = re.search(r"for (\d+\.\d+\.\d+\.\d+)", line)
        if m:
            hosts_found.append(m.group(1))
        yield line

    yield f"\n{len(hosts_found)} devices found. Checking for open ports..."
    yield "─" * 60

    # Port scan each host — sT = TCP connect, no sudo needed
    for host in hosts_found[:20]:
        yield f"\n▸ {host}"
        cmd_ports = (
            f"nmap -sT --open -T4 -p 21,22,23,80,443,445,554,1433,3306,3389,"
            f"5432,5900,6379,8080,8443,9200,27017 {host} 2>/dev/null | "
            f"grep -E 'open|PORT' | head -15"
        )
        port_lines = []
        async for line in vm.run(cmd_ports, timeout=30):
            port_lines.append(line)

        if not port_lines:
            yield "  ✓ No common risky ports open"
            continue

        for line in port_lines:
            m = re.match(r"(\d+)/tcp\s+open\s+(\S+)", line)
            if m:
                port = int(m.group(1))
                svc  = m.group(2)
                if port in RISK_PLAIN:
                    name, advice = RISK_PLAIN[port]
                    risk = "⚠" if port in (23, 21, 3306, 5432, 6379, 27017, 9200) else "ℹ"
                    yield f"  {risk} Port {port} ({name}) — {advice}"
                else:
                    yield f"  ℹ Port {port} ({svc}) open"

    yield "\n" + "─" * 60
    yield "[T] Scan complete. Review any ⚠ warnings above."


async def check_router_security(router_ip: str = "192.168.1.1") -> AsyncIterator[str]:
    """Check common router security issues."""
    yield f"[T] Router security check: {router_ip}"
    yield "─" * 50

    # Port scan — use TCP connect scan (no sudo needed)
    yield "\n[→] Open admin ports..."
    cmd1 = (
        f"nmap -sT -p 22,23,80,443,8080,8443,8888,7547 "
        f"--open {router_ip} 2>/dev/null | "
        f"grep -E 'open|filtered|PORT'"
    )
    found_any = False
    async for line in vm.run(cmd1, timeout=30):
        if line.strip():
            found_any = True
            port_num = line.split("/")[0].strip() if "/" in line else ""
            if port_num.isdigit() and int(port_num) in RISK_PLAIN:
                _, advice = RISK_PLAIN[int(port_num)]
                yield f"  ⚠ {line.strip()} — {advice}"
            else:
                yield f"  ℹ {line.strip()}"
    if not found_any:
        yield "  ✓ No common admin ports detected"

    # Web interface check
    yield "\n[→] Web interface accessible..."
    cmd2 = (
        f"curl -sL --connect-timeout 8 -o /dev/null -w '%{{http_code}} %{{url_effective}}' "
        f"'http://{router_ip}/' 2>/dev/null"
    )
    async for line in vm.run(cmd2, timeout=12):
        code = line.split()[0] if line.strip() else ""
        if code in ("200", "301", "302"):
            yield f"  ⚠ Admin interface accessible at http://{router_ip}/"
            yield "    Ensure default credentials have been changed"
        elif line.strip():
            yield f"  ℹ Response: {line.strip()}"

    # Check for telnet (always bad)
    yield "\n[→] Telnet check (insecure protocol)..."
    cmd3 = f"nmap -sT -p 23 --open {router_ip} 2>/dev/null | grep -E 'open'"
    has_telnet = False
    async for line in vm.run(cmd3, timeout=15):
        if "open" in line:
            has_telnet = True
            yield "  ✗ TELNET IS OPEN — this is a serious security risk"
            yield "    Disable telnet in router admin → Remote Management"
    if not has_telnet:
        yield "  ✓ Telnet not detected"

    # Default credentials check
    yield "\n[→] Default credential hints..."
    yield f"  Check: http://{router_ip}/ — try admin/admin, admin/password, admin/1234"
    yield "  If any work — change password immediately"

    yield "\n[T] Router check complete."
    yield "─" * 50
    yield "RECOMMENDATIONS:"
    yield "  1. Change default admin password"
    yield "  2. Disable remote management (WAN access)"
    yield "  3. Enable WPA3 or WPA2-AES WiFi encryption"
    yield "  4. Disable WPS (known vulnerability)"
    yield "  5. Keep firmware updated"


async def check_link_safety(url: str) -> AsyncIterator[str]:
    """Check if a URL is safe — phishing, malware, reputation."""
    yield f"[T] Link safety check: {url}"
    yield "─" * 50

    import urllib.parse
    parsed = urllib.parse.urlparse(url if "://" in url else "https://" + url)
    domain = parsed.netloc or url.split("/")[0]

    # Stage 1: Google Safe Browsing transparency report
    yield "[1/4] Google Safe Browsing status..."
    yield f"  Check: https://transparencyreport.google.com/safe-browsing/search?url={url}"
    cmd1 = (
        f"curl -sL --connect-timeout 10 "
        f"'https://transparencyreport.google.com/transparencyreport/api/v3/safebrowsing/status?site={domain}' "
        f"2>/dev/null | python3 -c \""
        f"import sys; data=sys.stdin.read(); "
        f"print('UNSAFE' if any(x in data for x in ['MALWARE','PHISHING','UNWANTED']) else 'No threats detected by Google')"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(cmd1, timeout=12):
        yield f"  {line}"

    # Stage 2: Domain WHOIS — age check
    yield "\n[2/4] Domain age and registration..."
    cmd2 = (
        f"whois {domain} 2>/dev/null | "
        f"grep -iE 'created|registered|registrar|expir' | "
        f"sort -u | head -6"
    )
    async for line in vm.run(cmd2, timeout=10):
        yield f"  {line}"

    # Stage 3: DNS check — does it resolve?
    yield "\n[3/4] DNS resolution check..."
    cmd3 = f"dig +short {domain} 2>/dev/null | head -5"
    results = []
    async for line in vm.run(cmd3, timeout=8):
        results.append(line)
        yield f"  {line}"
    if not results:
        yield "  ✗ Domain does not resolve — likely invalid or taken down"

    # Stage 4: Links for manual verification
    yield "\n[4/4] Manual verification links..."
    yield f"  VirusTotal:      https://www.virustotal.com/gui/url-search/{url}"
    yield f"  URLScan:         https://urlscan.io/search/#{domain}"
    yield f"  PhishTank:       https://www.phishtank.com/checkurl/?url={url}"
    yield f"  Google SB:       https://transparencyreport.google.com/safe-browsing/search?url={url}"


async def harden_device_advice(os_type: str = "windows") -> AsyncIterator[str]:
    """Give plain-language hardening advice for a device type."""
    yield f"[T] Device hardening guide — {os_type.upper()}"
    yield "─" * 60

    advice = {
        "windows": [
            ("Enable Windows Defender",     "Settings → Windows Security → Virus & threat protection → turn on"),
            ("Enable Firewall",             "Settings → Windows Security → Firewall → turn on for all networks"),
            ("Enable automatic updates",    "Settings → Windows Update → turn on automatic updates"),
            ("Use strong passwords",        "Settings → Accounts → Sign-in options → use PIN or strong password"),
            ("Enable BitLocker",            "Control Panel → BitLocker Drive Encryption → turn on"),
            ("Disable Remote Desktop",      "Settings → System → Remote Desktop → disable if not needed"),
            ("Check startup programs",      "Task Manager → Startup tab → disable unknown programs"),
            ("Enable 2FA on accounts",      "Google/Microsoft accounts → security settings → enable 2-step verification"),
        ],
        "android": [
            ("Enable screen lock",          "Settings → Security → Screen lock → PIN or fingerprint"),
            ("Enable Find My Device",       "Settings → Google → Find My Device → enable"),
            ("Keep OS updated",             "Settings → System → System update → check for updates"),
            ("Review app permissions",      "Settings → Apps → select each app → Permissions → review"),
            ("Enable Google Play Protect",  "Play Store → profile → Play Protect → enable"),
            ("Disable unknown sources",     "Settings → Apps → Special app access → Install unknown apps → disable all"),
            ("Use a VPN on public WiFi",    "Use trusted VPN app when on public networks"),
        ],
        "router": [
            ("Change default password",     "Router admin page → Administration → change from default credentials"),
            ("Enable WPA3 or WPA2",         "Router admin → Wireless → Security → set WPA3 or WPA2-AES"),
            ("Disable WPS",                 "Router admin → Wireless → WPS → disable (known vulnerability)"),
            ("Update firmware",             "Router admin → Administration → Firmware update → check for updates"),
            ("Disable remote management",   "Router admin → Administration → Remote Management → disable"),
            ("Use guest network",           "Create separate guest WiFi for visitors and IoT devices"),
            ("Check connected devices",     "Router admin → Device List → verify all devices are yours"),
        ],
    }

    steps = advice.get(os_type, advice["windows"])
    for i, (title, detail) in enumerate(steps, 1):
        yield f"{i}. {title}"
        yield f"   → {detail}"
        yield ""

    yield "[T] Follow these steps to significantly improve your security."
