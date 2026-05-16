"""
Intelligence orchestrator for T.
Entry point for all intel_action messages from engine.
Confirmation gate → dispatch → graph update → log.
"""

import asyncio
import time
from typing import TYPE_CHECKING
from core.logger import get_logger
from .graph import get_graph, reset_graph, parse_intel_output, IntelGraph

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("intel.orchestrator")

_pending: dict[str, asyncio.Future] = {}

_RISK_MAP: dict[str, str] = {
    "person_username":       "LOW",
    "person_email":          "LOW",
    "person_phone":          "LOW",
    "phone_dossier":         "MEDIUM",
    "person_name":           "LOW",
    "person_ip":             "LOW",
    "person_dossier":        "MEDIUM",
    "org_dns":               "LOW",
    "org_whois":             "LOW",
    "org_tech":              "LOW",
    "org_subdomains":        "LOW",
    "org_shodan":            "MEDIUM",
    "org_emails":            "MEDIUM",
    "org_full":              "HIGH",
    "breach_hibp":           "LOW",
    "breach_dehashed":       "MEDIUM",
    "breach_paste":          "LOW",
    "breach_combos":         "MEDIUM",
    "breach_wordlist":       "MEDIUM",
    "breach_password_check": "LOW",
    "darkweb_search":        "LOW",
    "darkweb_onion_search":  "MEDIUM",
    "darkweb_intelx":        "MEDIUM",
    "darkweb_paste_monitor": "LOW",
    "darkweb_email":         "MEDIUM",
    "darkweb_setup_tor":     "MEDIUM",
    "graph_reset":           "LOW",
}


async def handle_intel_action(client: "Client", msg: dict) -> None:
    action    = msg.get("action", "")
    params    = msg.get("params", {})
    action_id = msg.get("id", "")
    risk      = _RISK_MAP.get(action, "MEDIUM")

    command, description = _build_description(action, params)

    # ── Confirmation ──────────────────────────────────────────────────────────
    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    _pending[action_id] = fut

    await client.send({
        "type":        "intel_confirm_request",
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
        await client.send({"type": "intel_done", "id": action_id, "cancelled": True})
        return

    # ── Execute ───────────────────────────────────────────────────────────────
    started = time.time()
    log.info(f"intel action={action} params={params}")
    output_lines: list[str] = []

    try:
        async for chunk in _dispatch(action, params):
            output_lines.append(chunk)
            await client.send({
                "type":   "intel_stream",
                "id":     action_id,
                "action": action,
                "chunk":  chunk,
            })

        # Parse output into graph
        graph = get_graph()
        root_node = params.get("query", params.get("domain", params.get("email",
                     params.get("username", params.get("target", "root")))))
        if root_node:
            # Ensure root node exists
            root_type = _root_type(action)
            graph.add_node(root_node, root_type, root_node)
            parse_intel_output(output_lines, root_node, graph)

        await client.send({
            "type":     "intel_done",
            "id":       action_id,
            "action":   action,
            "duration": round(time.time() - started, 1),
            "graph":    graph.to_dict(),
        })

    except Exception as e:
        await client.send({"type": "intel_error", "id": action_id, "error": str(e)})


async def handle_intel_confirm(client: "Client", msg: dict) -> None:
    action_id = msg.get("id", "")
    confirmed = bool(msg.get("confirmed", False))
    fut = _pending.pop(action_id, None)
    if fut and not fut.done():
        fut.set_result(confirmed)


async def handle_intel_graph_reset(client: "Client") -> None:
    reset_graph()
    await client.send({"type": "intel_graph", "graph": get_graph().to_dict()})


async def handle_intel_graph_get(client: "Client") -> None:
    await client.send({"type": "intel_graph", "graph": get_graph().to_dict()})


# ── Dispatch ──────────────────────────────────────────────────────────────────

async def _dispatch(action: str, p: dict):
    from . import person, org, breach, darkweb

    # ── Person intel ──────────────────────────────────────────────────────────
    if action == "person_username":
        async for l in person.profile_username(p["query"]): yield l
    elif action == "person_email":
        async for l in person.profile_email(p["query"]): yield l
    elif action == "person_phone":
        async for l in person.profile_phone(p["query"]): yield l
    elif action == "phone_dossier":
        async for l in person.phone_full_dossier(p["query"]): yield l
    elif action == "person_name":
        parts = p["query"].split(" ", 1)
        async for l in person.profile_name(parts[0], parts[1] if len(parts) > 1 else ""): yield l
    elif action == "person_ip":
        async for l in person.profile_ip_geolocation(p["query"]): yield l
    elif action == "person_dossier":
        async for l in person.build_full_dossier(p["query"], p.get("query_type", "username")): yield l

    # ── Org intel ─────────────────────────────────────────────────────────────
    elif action == "org_dns":
        async for l in org.dns_footprint(p["domain"]): yield l
    elif action == "org_whois":
        async for l in org.whois_profile(p["domain"]): yield l
    elif action == "org_tech":
        async for l in org.tech_stack(p["domain"]): yield l
    elif action == "org_subdomains":
        async for l in org.subdomain_harvest(p["domain"]): yield l
    elif action == "org_shodan":
        async for l in org.shodan_footprint(p["domain"]): yield l
    elif action == "org_emails":
        async for l in org.email_harvest(p["domain"]): yield l
    elif action == "org_full":
        async for l in org.full_org_footprint(p["domain"]): yield l

    # ── Breach intel ──────────────────────────────────────────────────────────
    elif action == "breach_hibp":
        async for l in breach.check_hibp(p["email"], p.get("api_key", "")): yield l
    elif action == "breach_dehashed":
        async for l in breach.check_dehashed(p["query"], p.get("query_type", "email")): yield l
    elif action == "breach_paste":
        async for l in breach.search_paste_sites(p["query"]): yield l
    elif action == "breach_combos":
        async for l in breach.search_combo_lists(p["query"]): yield l
    elif action == "breach_wordlist":
        async for l in breach.gen_targeted_wordlist(p): yield l
    elif action == "breach_password_check":
        async for l in breach.check_password_breach(p["password"]): yield l

    # ── Dark web intel ────────────────────────────────────────────────────────
    elif action == "darkweb_setup_tor":
        async for l in darkweb.setup_tor_proxy(): yield l
    elif action == "darkweb_search":
        async for l in darkweb.tor_search(p["query"]): yield l
    elif action == "darkweb_onion_search":
        async for l in darkweb.onion_search_via_tor(p["query"]): yield l
    elif action == "darkweb_intelx":
        async for l in darkweb.intelx_search(p["query"], p.get("api_key", "")): yield l
    elif action == "darkweb_paste_monitor":
        async for l in darkweb.monitor_paste_sites(p["query"], int(p.get("duration", 30))): yield l
    elif action == "darkweb_email":
        async for l in darkweb.darkweb_email_search(p["email"]): yield l
    elif action == "darkweb_onions":
        async for l in darkweb.list_known_onions(): yield l

    else:
        yield f"[ERROR] Unknown intel action: {action}"


# ── Description builder ───────────────────────────────────────────────────────

def _build_description(action: str, p: dict) -> tuple[str, str]:
    q = p.get("query", p.get("domain", p.get("email", p.get("username", "?"))))
    DESCS = {
        "person_username":       (f"sherlock + maigret {q}", f"Search '{q}' across 3000+ platforms"),
        "person_email":          (f"holehe + whois {q}",     f"Email intelligence on {q}"),
        "person_phone":          (f"phoneinfoga {q}",         f"Deep phone intelligence on {q} — 9 sources"),
        "phone_dossier":         (f"full dossier from phone: {q}", f"Complete person dossier from phone number {q} — carrier → name → social accounts → breach → dark web → relationship graph"),
        "person_name":           (f"theharvester + recon-ng '{q}'", f"Name-based OSINT for '{q}'"),
        "person_dossier":        (f"full dossier build: {q}", f"Complete person profile from {q}"),
        "org_full":              (f"full org footprint: {q}", f"Complete org intelligence on {q}: WHOIS, DNS, subdomains, tech stack, emails, Shodan"),
        "org_subdomains":        (f"subfinder + amass + crt.sh {q}", f"Subdomain discovery for {q}"),
        "org_emails":            (f"theHarvester {q}",        f"Email harvest for domain {q}"),
        "org_shodan":            (f"shodan {q}",              f"Shodan exposed services for {q}"),
        "breach_hibp":           (f"hibp check {q}",          f"Check {q} against HaveIBeenPwned"),
        "breach_paste":          (f"paste search {q}",        f"Search paste sites for '{q}'"),
        "breach_wordlist":       ("cupp -i",                  "Generate targeted wordlist from personal info"),
        "breach_password_check": ("hibp k-anon check",        "Check if password appears in known breaches (k-anonymity, password never transmitted)"),
        "darkweb_search":        (f"ahmia search: {q}",       f"Dark web search for '{q}' via Ahmia index"),
        "darkweb_email":         (f"darkweb email: {q}",      f"Search dark web for {q}"),
        "darkweb_paste_monitor": (f"paste monitor: {q}",      f"Monitor paste sites for '{q}' for {p.get('duration', 30)}s"),
        "darkweb_setup_tor":     ("tor + proxychains setup",  "Install and start Tor on VM, verify Tor IP"),
    }
    entry = DESCS.get(action)
    if entry:
        return entry
    return f"{action} {q}", f"Intel: {action} on {q}"


def _root_type(action: str) -> str:
    if action.startswith("person_"):
        return "person"
    if action.startswith("org_"):
        return "org"
    if action.startswith("breach_"):
        return "breach"
    if action.startswith("darkweb_"):
        return "domain"
    return "person"
