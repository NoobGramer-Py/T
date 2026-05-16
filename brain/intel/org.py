"""
Organisation intelligence module for T.
Builds a complete footprint of a company or domain.
"""

from typing import AsyncIterator
from offensive.vm_bridge import vm
from core.logger import get_logger

log = get_logger("intel.org")


async def dns_footprint(domain: str) -> AsyncIterator[str]:
    """Full DNS enumeration: A, MX, NS, TXT, CNAME, zone transfer attempt."""
    yield f"[T] DNS footprint: {domain}"
    yield "─" * 50

    yield "[1/4] DNS records (A, MX, NS, TXT, CNAME)..."
    cmd = (
        f"for t in A MX NS TXT CNAME SOA; do "
        f"echo \"--- $t ---\"; "
        f"dig +short $t {domain} 2>/dev/null; "
        f"done"
    )
    async for line in vm.run(cmd, timeout=30):
        yield line

    yield "\n[2/4] Zone transfer attempt..."
    cmd2 = f"dig axfr {domain} 2>/dev/null | head -30"
    async for line in vm.run(cmd2, timeout=15):
        yield line

    yield "\n[3/4] Subdomain enumeration (dnsrecon)..."
    cmd3 = f"dnsrecon -d {domain} -t std 2>/dev/null | head -40"
    async for line in vm.run(cmd3, timeout=60):
        yield line

    yield "\n[4/4] DNS brute force (top subdomains)..."
    cmd4 = f"dnsx -d {domain} -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -silent 2>/dev/null | head -30"
    async for line in vm.run(cmd4, timeout=60):
        yield line


async def whois_profile(domain: str) -> AsyncIterator[str]:
    """WHOIS registration data: registrant, dates, nameservers, registrar."""
    yield f"[T] WHOIS: {domain}"
    cmd = (
        f"whois {domain} 2>/dev/null | "
        f"grep -iE 'registrant|admin|tech|name|email|phone|org|creation|expir|registrar|name.server' "
        f"| grep -v '^%' | sort -u | head -30"
    )
    async for line in vm.run(cmd, timeout=20):
        yield line


async def tech_stack(domain: str) -> AsyncIterator[str]:
    """Detect web technologies: CMS, frameworks, CDN, analytics, servers."""
    yield f"[T] Technology stack: {domain}"

    yield "[1/2] WhatWeb fingerprint..."
    cmd = f"whatweb -a 3 {domain} 2>/dev/null"
    async for line in vm.run(cmd, timeout=30):
        yield line

    yield "\n[2/2] HTTP headers analysis..."
    cmd2 = (
        f"curl -sIL --connect-timeout 8 https://{domain} 2>/dev/null | "
        f"grep -iE 'server:|x-powered-by:|x-generator:|cf-ray:|via:|x-frame:|strict-transport:|content-security:'"
    )
    async for line in vm.run(cmd2, timeout=15):
        yield line


async def subdomain_harvest(domain: str) -> AsyncIterator[str]:
    """Multi-source subdomain discovery: passive + active."""
    yield f"[T] Subdomain harvest: {domain}"

    yield "[1/3] Subfinder (passive APIs)..."
    cmd = f"subfinder -d {domain} -silent 2>/dev/null | sort -u"
    async for line in vm.run(cmd, timeout=120):
        yield line

    yield "\n[2/3] Amass passive enumeration..."
    cmd2 = f"amass enum -passive -d {domain} 2>/dev/null | head -50"
    async for line in vm.run(cmd2, timeout=120):
        yield line

    yield "\n[3/3] Certificate transparency (crt.sh)..."
    cmd3 = (
        f"curl -sL 'https://crt.sh/?q=%25.{domain}&output=json' 2>/dev/null | "
        f"python3 -c \"import sys,json; "
        f"data=json.load(sys.stdin); "
        f"names=sorted(set(e['name_value'] for e in data)); "
        f"[print(n) for n in names[:50]]\" 2>/dev/null"
    )
    async for line in vm.run(cmd3, timeout=20):
        yield line


async def shodan_footprint(domain: str) -> AsyncIterator[str]:
    """Shodan scan: exposed services, ports, banners, CVEs on all IPs."""
    yield f"[T] Shodan footprint: {domain}"

    yield "[1/2] Domain search..."
    cmd = f"shodan search 'hostname:{domain}' --fields ip_str,port,product,version,vulns 2>/dev/null | head -30"
    async for line in vm.run(cmd, timeout=30):
        yield line

    yield "\n[2/2] Resolve + Shodan host lookup..."
    cmd2 = (
        f"IP=$(dig +short A {domain} 2>/dev/null | head -1); "
        f"echo \"IP: $IP\"; "
        f"[ -n \"$IP\" ] && shodan host $IP 2>/dev/null | head -40"
    )
    async for line in vm.run(cmd2, timeout=30):
        yield line


async def email_harvest(domain: str) -> AsyncIterator[str]:
    """Harvest employee emails associated with the domain."""
    yield f"[T] Email harvest: {domain}"

    yield "[1/2] theHarvester (multi-source)..."
    cmd = f"theHarvester -d {domain} -b google,bing,yahoo,linkedin,twitter -l 100 2>/dev/null | grep '@' | sort -u | head -50"
    async for line in vm.run(cmd, timeout=90):
        yield line

    yield "\n[2/2] Hunter.io format check..."
    cmd2 = (
        f"curl -sL 'https://hunter.io/email-finder/search?domain={domain}' 2>/dev/null | "
        f"python3 -c \"import sys,re; "
        f"emails=re.findall(r'[a-zA-Z0-9._%+-]+@{domain}', sys.stdin.read()); "
        f"[print(e) for e in sorted(set(emails))[:30]]\" 2>/dev/null"
    )
    async for line in vm.run(cmd2, timeout=15):
        yield line


async def full_org_footprint(domain: str) -> AsyncIterator[str]:
    """Complete organisation intelligence pipeline."""
    yield f"[T] Full org intelligence: {domain}"
    yield "═" * 60

    yield "\n[1/6] WHOIS registration data..."
    async for l in whois_profile(domain): yield l

    yield "\n[2/6] DNS footprint..."
    async for l in dns_footprint(domain): yield l

    yield "\n[3/6] Subdomain discovery..."
    async for l in subdomain_harvest(domain): yield l

    yield "\n[4/6] Technology stack..."
    async for l in tech_stack(domain): yield l

    yield "\n[5/6] Employee email harvest..."
    async for l in email_harvest(domain): yield l

    yield "\n[6/6] Shodan exposed services..."
    async for l in shodan_footprint(domain): yield l

    yield "\n═" * 60
    yield "[T] Org intelligence complete."
