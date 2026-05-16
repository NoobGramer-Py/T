"""
Tool catalog for T's offensive security module.
Single source of truth for every tool T can invoke on the attack VM.
Each entry defines: binary name, category, install command, risk level,
description, and whether it requires monitor-mode wifi adapter.
"""

from dataclasses import dataclass, field
from typing import Literal

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@dataclass(frozen=True)
class Tool:
    name:        str            # binary name as invoked on VM
    category:    str
    description: str
    install_cmd: str            # apt/pip/gem/go install command
    risk:        RiskLevel
    needs_wifi:  bool = False   # requires wireless adapter in monitor mode


# ── Catalog ───────────────────────────────────────────────────────────────────

CATALOG: list[Tool] = [

    # ── Reconnaissance ────────────────────────────────────────────────────────
    Tool("nmap",        "recon", "Port/service/OS/vuln scanning",
         "apt install -y nmap",                                      "MEDIUM"),
    Tool("masscan",     "recon", "Ultra-fast large-scale port scanner",
         "apt install -y masscan",                                   "MEDIUM"),
    Tool("amass",       "recon", "Subdomain enumeration and DNS mapping",
         "apt install -y amass",                                     "LOW"),
    Tool("subfinder",   "recon", "Passive subdomain discovery (APIs)",
         "go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
         "LOW"),
    Tool("theharvester","recon", "Email, subdomain, IP from public sources",
         "apt install -y theharvester",                              "LOW"),
    Tool("recon-ng",    "recon", "Modular OSINT and recon framework",
         "apt install -y recon-ng",                                  "LOW"),
    Tool("whatweb",     "recon", "Web technology fingerprinting",
         "apt install -y whatweb",                                   "LOW"),
    Tool("shodan",      "recon", "Search Shodan for exposed hosts/services",
         "pip3 install -q shodan",                                   "LOW"),
    Tool("dnsx",        "recon", "DNS resolution and bruteforce at scale",
         "go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest",
         "LOW"),
    Tool("whois",       "recon", "Domain/IP registration information",
         "apt install -y whois",                                     "LOW"),
    Tool("dnsrecon",    "recon", "DNS enumeration and zone transfer checks",
         "apt install -y dnsrecon",                                  "LOW"),
    Tool("fierce",      "recon", "DNS brute force and subdomain discovery",
         "pip3 install -q fierce",                                   "LOW"),

    # ── Web Application ───────────────────────────────────────────────────────
    Tool("nikto",       "web", "Web server vulnerability scanner",
         "apt install -y nikto",                                     "MEDIUM"),
    Tool("sqlmap",      "web", "Automated SQL injection detection and exploitation",
         "apt install -y sqlmap",                                    "HIGH"),
    Tool("ffuf",        "web", "Fast web fuzzer — dirs, params, vhosts, headers",
         "apt install -y ffuf",                                      "MEDIUM"),
    Tool("wfuzz",       "web", "Advanced web application fuzzer",
         "apt install -y wfuzz",                                     "MEDIUM"),
    Tool("gobuster",    "web", "Directory, DNS, and vhost brute force",
         "apt install -y gobuster",                                  "MEDIUM"),
    Tool("wpscan",      "web", "WordPress vulnerability and user scanner",
         "gem install wpscan",                                       "MEDIUM"),
    Tool("xsstrike",    "web", "XSS detection, fuzzing and exploitation",
         "pip3 install -q xsstrike",                                 "HIGH"),
    Tool("commix",      "web", "Command injection detection and exploitation",
         "apt install -y commix",                                    "HIGH"),
    Tool("feroxbuster", "web", "Recursive content discovery scanner",
         "apt install -y feroxbuster",                               "MEDIUM"),
    Tool("nuclei",      "web", "Template-based vulnerability scanner (1000s of templates)",
         "go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
         "MEDIUM"),
    Tool("wafw00f",     "web", "Web application firewall detection",
         "pip3 install -q wafw00f",                                  "LOW"),

    # ── Password Attacks ──────────────────────────────────────────────────────
    Tool("hashcat",     "crack", "GPU-accelerated hash cracking (NTLM, MD5, SHA, WPA…)",
         "apt install -y hashcat",                                   "MEDIUM"),
    Tool("john",        "crack", "CPU hash cracking with rule sets",
         "apt install -y john",                                      "MEDIUM"),
    Tool("hydra",       "crack", "Online brute force — SSH, FTP, HTTP, SMB, RDP…",
         "apt install -y hydra",                                     "HIGH"),
    Tool("medusa",      "crack", "Parallel online brute force",
         "apt install -y medusa",                                    "HIGH"),
    Tool("crunch",      "crack", "Custom wordlist generator by charset and length",
         "apt install -y crunch",                                    "LOW"),
    Tool("cewl",        "crack", "Website-scraping custom wordlist generator",
         "apt install -y cewl",                                      "LOW"),
    Tool("cupp",        "crack", "Common User Passwords Profiler (targeted wordlist)",
         "apt install -y cupp",                                      "LOW"),

    # ── Exploitation ──────────────────────────────────────────────────────────
    Tool("msfconsole",  "exploit", "Metasploit Framework — full exploitation suite",
         "apt install -y metasploit-framework",                      "CRITICAL"),
    Tool("msfvenom",    "payload", "Metasploit payload generator",
         "apt install -y metasploit-framework",                      "CRITICAL"),
    Tool("searchsploit","exploit", "Local exploit-db offline search",
         "apt install -y exploitdb",                                 "LOW"),
    Tool("beef-xss",    "exploit", "Browser Exploitation Framework (XSS pivot)",
         "apt install -y beef-xss",                                  "HIGH"),
    Tool("routersploit","exploit", "Router and embedded device exploitation",
         "pip3 install -q routersploit",                             "HIGH"),

    # ── WiFi ─────────────────────────────────────────────────────────────────
    Tool("airmon-ng",   "wifi", "Enable/disable wireless monitor mode",
         "apt install -y aircrack-ng",                               "HIGH",    needs_wifi=True),
    Tool("airodump-ng", "wifi", "Wireless packet capture and client tracking",
         "apt install -y aircrack-ng",                               "HIGH",    needs_wifi=True),
    Tool("aireplay-ng", "wifi", "Packet injection — deauth, replay, chop-chop",
         "apt install -y aircrack-ng",                               "CRITICAL",needs_wifi=True),
    Tool("aircrack-ng", "wifi", "WEP/WPA handshake cracking",
         "apt install -y aircrack-ng",                               "HIGH",    needs_wifi=True),
    Tool("hcxdumptool", "wifi", "PMKID/EAPOL handshake capture (clientless)",
         "apt install -y hcxdumptool",                               "CRITICAL",needs_wifi=True),
    Tool("hcxtools",    "wifi", "Convert captures to hashcat-compatible format",
         "apt install -y hcxtools",                                  "MEDIUM"),
    Tool("wifite",      "wifi", "Automated wireless auditing tool",
         "apt install -y wifite",                                    "CRITICAL",needs_wifi=True),
    Tool("bettercap",   "wifi", "WiFi, BLE, and network swiss-army-knife",
         "apt install -y bettercap",                                 "CRITICAL",needs_wifi=True),

    # ── MITM & Network ────────────────────────────────────────────────────────
    Tool("ettercap",    "mitm", "MITM ARP poisoning + traffic sniffing",
         "apt install -y ettercap-text-only",                        "CRITICAL"),
    Tool("arpspoof",    "mitm", "ARP cache poisoning",
         "apt install -y dsniff",                                    "CRITICAL"),
    Tool("mitmproxy",   "mitm", "Interactive TLS/HTTPS MITM proxy",
         "apt install -y mitmproxy",                                 "HIGH"),
    Tool("sslstrip",    "mitm", "SSL stripping (downgrades HTTPS → HTTP)",
         "pip3 install -q sslstrip",                                 "CRITICAL"),
    Tool("responder",   "mitm", "LLMNR/NBT-NS poisoner and hash capture",
         "apt install -y responder",                                 "CRITICAL"),
    Tool("tcpdump",     "mitm", "Command-line packet capture",
         "apt install -y tcpdump",                                   "MEDIUM"),
    Tool("tshark",      "mitm", "Wireshark CLI packet capture and analysis",
         "apt install -y tshark",                                    "MEDIUM"),
    Tool("netcat",      "mitm", "Raw TCP/UDP connections and listeners",
         "apt install -y netcat-openbsd",                            "MEDIUM"),

    # ── Payload & Evasion ─────────────────────────────────────────────────────
    Tool("veil",        "payload", "AV-evading payload generator",
         "apt install -y veil",                                      "CRITICAL"),
    Tool("upx",         "payload", "Binary packer and compressor",
         "apt install -y upx",                                       "MEDIUM"),

    # ── Stealth & Evasion (Phase 13) ──────────────────────────────────────────
    Tool("clamscan",    "stealth", "Local AV signature scanner",
         "apt install -y clamav",                                    "LOW"),
    Tool("yara",        "stealth", "YARA rule-based payload detection",
         "apt install -y yara",                                      "LOW"),
    Tool("shred",       "stealth", "Secure file deletion (multi-pass overwrite)",
         "apt install -y coreutils",                                 "MEDIUM"),
    Tool("srm",         "stealth", "Secure rm replacement",
         "apt install -y secure-delete",                             "MEDIUM"),
    Tool("bleachbit",   "stealth", "System artifact cleaner",
         "apt install -y bleachbit",                                 "MEDIUM"),

    # ── OSINT & Location ──────────────────────────────────────────────────────
    Tool("phoneinfoga", "osint", "Phone number OSINT — carrier, region, social accounts",
         "pip3 install -q phoneinfoga",                              "LOW"),
    Tool("sherlock",    "osint", "Username search across 300+ social platforms",
         "pip3 install -q sherlock-project",                         "LOW"),
    Tool("holehe",      "osint", "Email → account existence check (70+ sites)",
         "pip3 install -q holehe",                                   "LOW"),
    Tool("maigret",     "osint", "Username OSINT across 3000+ sites",
         "pip3 install -q maigret",                                  "LOW"),
    Tool("exiftool",    "osint", "Extract GPS, author, software metadata from files",
         "apt install -y libimage-exiftool-perl",                    "LOW"),
    Tool("osrframework", "osint", "Username/email/DNS multi-service OSINT",
         "pip3 install -q osrframework",                             "LOW"),

    # ── Forensics & Steganography ─────────────────────────────────────────────
    Tool("binwalk",     "forensics", "Firmware and binary analysis / extraction",
         "apt install -y binwalk",                                   "LOW"),
    Tool("steghide",    "forensics", "Steganography — hide/extract data in images/audio",
         "apt install -y steghide",                                  "LOW"),
    Tool("foremost",    "forensics", "File carving from disk images",
         "apt install -y foremost",                                  "LOW"),
    Tool("strings",     "forensics", "Extract printable strings from any binary",
         "apt install -y binutils",                                  "LOW"),
    Tool("volatility3", "forensics", "Memory forensics — processes, network, registry",
         "pip3 install -q volatility3",                              "LOW"),

    # ── Phase 13: Stealth & Evasion ───────────────────────────────────────────
    Tool("encode_payload",      "stealth", "XOR/Base64/Shikata encode payload to evade AV signatures",
         "echo 'built-in'",                                          "HIGH"),
    Tool("generate_evasive_payload", "stealth", "msfvenom payload with multi-layer encoding and HTTPS staging",
         "echo 'msfvenom built-in'",                                 "CRITICAL"),
    Tool("clear_logs_linux",    "stealth", "Wipe Linux auth/syslog/messages/bash_history via session",
         "echo 'built-in'",                                          "CRITICAL"),
    Tool("clear_logs_windows",  "stealth", "wevtutil clear System/Security/Application event logs",
         "echo 'built-in'",                                          "CRITICAL"),
    Tool("migrate_process",     "stealth", "Migrate Meterpreter into trusted process (explorer.exe etc.)",
         "echo 'built-in'",                                          "HIGH"),
    Tool("timestomp",           "stealth", "Randomise file timestamps to defeat timeline forensics",
         "echo 'built-in'",                                          "HIGH"),
    Tool("lolbins_enum",        "stealth", "Enumerate Living-off-the-Land binaries on target",
         "echo 'built-in'",                                          "MEDIUM"),
    Tool("ps_amsi_bypass",      "stealth", "PowerShell AMSI + execution policy bypass with encoded payload",
         "echo 'built-in'",                                          "HIGH"),
    Tool("full_stealth_sweep",  "stealth", "Full post-exploitation stealth: migrate → clear logs → timestomp → LOLBins",
         "echo 'built-in'",                                          "CRITICAL"),
    Tool("iodine",              "stealth", "DNS tunneling — covert C2 channel over DNS queries",
         "apt install -y iodine",                                     "HIGH"),
    Tool("proxychains",         "stealth", "Route attack traffic through proxy chain for anonymity",
         "apt install -y proxychains4",                               "MEDIUM"),
    Tool("tor",                 "stealth", "Route traffic through Tor network",
         "apt install -y tor",                                        "MEDIUM"),
]

# Fast lookup by name
_by_name: dict[str, Tool] = {t.name: t for t in CATALOG}

# Group by category
_by_category: dict[str, list[Tool]] = {}
for _t in CATALOG:
    _by_category.setdefault(_t.category, []).append(_t)


def get(name: str) -> Tool | None:
    return _by_name.get(name)


def by_category(category: str) -> list[Tool]:
    return _by_category.get(category, [])


def all_tools() -> list[Tool]:
    return CATALOG


def categories() -> list[str]:
    return list(_by_category.keys())
