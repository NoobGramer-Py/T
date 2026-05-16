"""
Person profiling module for T's intelligence system.
Builds a complete dossier on a person from minimal input.
All tools run on the attack VM via vm_bridge.
PATH is explicitly extended so ~/.local/bin tools (sherlock, maigret, phoneinfoga) are found.
"""

import re
from typing import AsyncIterator
from offensive.vm_bridge import vm
from core.logger import get_logger

log = get_logger("intel.person")

# Prepended to every SSH command so user-installed tools are found
_PATH = "PATH=$PATH:$HOME/.local/bin:/usr/local/bin:/usr/bin "

# Country code → (country name, common carriers)
_CC_MAP: dict[str, tuple[str, str]] = {
    "92":  ("Pakistan",     "Jazz / Zong / Telenor / Ufone"),
    "1":   ("US/Canada",    "AT&T / Verizon / T-Mobile"),
    "44":  ("UK",           "EE / O2 / Vodafone"),
    "91":  ("India",        "Airtel / Jio / Vi"),
    "971": ("UAE",          "Etisalat / du"),
    "966": ("Saudi Arabia", "STC / Mobily"),
    "20":  ("Egypt",        "Vodafone / Etisalat / Orange"),
    "49":  ("Germany",      "Deutsche Telekom / Vodafone"),
    "33":  ("France",       "Orange / SFR / Bouygues"),
    "7":   ("Russia",       "MTS / Beeline / MegaFon"),
    "86":  ("China",        "China Mobile / Unicom / Telecom"),
    "81":  ("Japan",        "NTT Docomo / SoftBank / au"),
    "82":  ("South Korea",  "SKT / KT / LG U+"),
    "55":  ("Brazil",       "Vivo / Claro / TIM"),
    "61":  ("Australia",    "Telstra / Optus / Vodafone"),
    "27":  ("South Africa", "Vodacom / MTN / Cell C"),
    "234": ("Nigeria",      "MTN / Airtel / Glo"),
    "254": ("Kenya",        "Safaricom / Airtel"),
}


def _resolve_cc(digits: str) -> tuple[str, str, str]:
    """Return (country, carriers, national_number) from E.164 digits."""
    cc = next(
        (c for c in sorted(_CC_MAP, key=len, reverse=True) if digits.startswith(c)),
        None,
    )
    if cc:
        country, carriers = _CC_MAP[cc]
        return country, carriers, digits[len(cc):]
    return "Unknown", "Unknown", digits


async def profile_username(username: str) -> AsyncIterator[str]:
    """Search username across 3000+ platforms (Sherlock + Maigret)."""
    yield f"[T] Username intelligence: {username}"
    yield "─" * 50

    yield "[1/2] Sherlock — 300+ social platforms..."
    cmd = f"{_PATH}sherlock {username} --timeout 10 --print-found 2>/dev/null"
    async for line in vm.run(cmd, timeout=120):
        yield line

    yield "\n[2/2] Maigret — 3000+ platforms..."
    cmd2 = (
        f"{_PATH}maigret {username} --timeout 15 -a --no-color --no-progressbar 2>/dev/null "
        f"| grep -E '^\\[\\+\\]|^\\[!\\]' | head -60"
    )
    async for line in vm.run(cmd2, timeout=180):
        yield line


async def profile_email(email: str) -> AsyncIterator[str]:
    """Email intelligence: account discovery, breach check, social links."""
    yield f"[T] Email intelligence: {email}"
    yield "─" * 50

    yield "[1/3] Holehe — account existence across 70+ sites..."
    cmd = f"{_PATH}holehe {email} --only-used --no-color 2>/dev/null"
    async for line in vm.run(cmd, timeout=120):
        yield line

    yield "\n[2/3] Email domain WHOIS..."
    domain = email.split("@")[-1] if "@" in email else email
    cmd2 = (
        f"whois {domain} 2>/dev/null | "
        f"grep -iE 'Registrant|Admin|Tech|Name|Email|Phone|Org|Creation|Expiry' "
        f"| grep -v '^%' | sort -u | head -20"
    )
    async for line in vm.run(cmd2, timeout=20):
        yield line

    yield "\n[3/3] MX record check..."
    cmd3 = f"dig +short MX {domain} 2>/dev/null && dig +short A {domain} 2>/dev/null"
    async for line in vm.run(cmd3, timeout=10):
        yield line


async def profile_phone(phone: str) -> AsyncIterator[str]:
    """
    Deep phone number intelligence — 9 stages.
    No paid API keys required.
    """
    phone    = phone.strip()
    digits   = re.sub(r"[^0-9]", "", phone)
    country, carriers, national = _resolve_cc(digits)

    yield f"[T] Phone intelligence: {phone}"
    yield "─" * 60

    # ── Stage 1: PhoneInfoga ──────────────────────────────────────────────────
    yield "\n[1/9] PhoneInfoga — carrier, region, number type..."
    cmd1 = f"{_PATH}phoneinfoga scan -n '{phone}' 2>/dev/null"
    async for line in vm.run(cmd1, timeout=60):
        yield line

    # ── Stage 2: Number format analysis ──────────────────────────────────────
    yield "\n[2/9] Number format analysis..."
    yield f"Raw:              {phone}"
    yield f"Digits only:      {digits}"
    yield f"Length:           {len(digits)}"
    yield f"Country code:     92 ({country})" if digits.startswith("92") else f"Country:          {country}"
    yield f"Possible carrier: {carriers}"
    yield f"National number:  {national}"
    yield f"E.164 format:     +{digits}"
    digits_only = digits  # alias used below

    # ── Stage 3: Carrier hints (no API key needed) ────────────────────────────
    yield "\n[3/9] Carrier analysis..."
    yield f"Country:          {country}"
    yield f"Possible carriers:{carriers}"
    # Pakistan-specific prefix mapping
    if digits.startswith("92"):
        nat = digits[2:]
        pk_map = {
            "300": "Ufone", "301": "Ufone", "302": "Ufone", "303": "Ufone",
            "304": "Ufone", "305": "Ufone", "306": "Ufone",
            "310": "Zong",  "311": "Zong",  "312": "Zong",  "313": "Zong",
            "314": "Zong",  "315": "Zong",  "316": "Zong",  "317": "Zong",
            "318": "Zong",  "319": "Zong",
            "320": "Jazz",  "321": "Jazz",  "322": "Jazz",  "323": "Jazz",
            "324": "Jazz",  "325": "Jazz",  "326": "Jazz",  "327": "Jazz",
            "328": "Jazz",  "329": "Jazz",
            "330": "Jazz",  "331": "Jazz",  "332": "Jazz",  "333": "Jazz",
            "334": "Jazz",  "335": "Jazz",  "336": "Jazz",  "337": "Jazz",
            "345": "Telenor", "346": "Telenor", "347": "Telenor",
            "348": "Telenor", "349": "Telenor",
            "340": "Telenor", "341": "Telenor", "342": "Telenor",
            "343": "Telenor", "344": "Telenor",
        }
        prefix3 = nat[:3]
        carrier = pk_map.get(prefix3, "Unknown")
        yield f"Pakistan prefix:  {prefix3}x → {carrier}"

    # ── Stage 4: WhatsApp / Telegram ─────────────────────────────────────────
    yield "\n[4/9] Messaging app presence check..."
    yield f"WhatsApp check:   https://wa.me/{digits}"
    yield f"Telegram link:    https://t.me/+{phone}"
    yield f"Viber link:       https://viber.com/{digits}"
    yield "(Open links in browser to verify account existence)"

    # WhatsApp HTTP check
    wa_cmd = (
        f"curl -sL --connect-timeout 8 -A 'WhatsApp/2.24' "
        f"'https://wa.me/{digits}' 2>/dev/null | "
        f"grep -c 'Open WhatsApp\\|wa.me' 2>/dev/null"
    )
    async for line in vm.run(wa_cmd, timeout=12):
        try:
            if int(line.strip()) > 0:
                yield "WhatsApp:         ACCOUNT EXISTS"
            else:
                yield "WhatsApp:         Status unknown"
        except ValueError:
            pass

    # ── Stage 5: Social media search links ───────────────────────────────────
    yield "\n[5/9] Social media search links..."
    yield f"Facebook:         https://www.facebook.com/search/top?q={phone}"
    yield f"TruePeopleSearch: https://www.truepeoplesearch.com/results?phoneno={digits}"
    yield f"Spokeo:           https://www.spokeo.com/phone/{digits}"
    yield f"WhitePages:       https://www.whitepages.com/phone/1-{digits}"
    yield f"AnyWho:           https://www.anywho.com/tel/{digits}"
    yield f"BeenVerified:     https://www.beenverified.com/phone/{digits}"

    # ── Stage 6: Breach and paste site search ────────────────────────────────
    yield "\n[6/9] Breach and leak database search..."
    paste_cmd = (
        f"curl -sL --connect-timeout 10 "
        f"'https://psbdmp.ws/api/v3/search/{digits}' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,json; d=json.load(sys.stdin); "
        f"data=d if isinstance(d,list) else d.get('data',[]); "
        f"print(f'Paste hits: {{len(data)}}'); "
        f"[print(f'  {{p.get(\\\"id\\\")}} | {{p.get(\\\"title\\\",\\\"no title\\\")}} — https://pastebin.com/{{p.get(\\\"id\\\")}}') for p in (data[:5] if data else [])]"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(paste_cmd, timeout=15):
        yield line

    github_cmd = (
        f"curl -sL --connect-timeout 10 "
        f"-H 'Accept: application/vnd.github.v3+json' "
        f"'https://api.github.com/search/code?q=%22{digits}%22&per_page=3' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,json; d=json.load(sys.stdin); "
        f"items=d.get('items',[])[:3]; "
        f"print(f'GitHub hits: {{d.get(\\\"total_count\\\",0)}}'); "
        f"[print(f'  {{i[\\\"repository\\\"][\\\"full_name\\\"]}}: {{i[\\\"html_url\\\"]}}') for i in items]"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(github_cmd, timeout=15):
        yield line

    # ── Stage 7: Dark web search ──────────────────────────────────────────────
    yield "\n[7/9] Dark web search (Ahmia index)..."
    dw_cmd = (
        f"curl -sL --connect-timeout 10 "
        f"'https://ahmia.fi/search/?q={digits}' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,re; html=sys.stdin.read(); "
        f"titles=re.findall(r'<h4[^>]*>.*?<a[^>]*href=\\\"([^\\\"]+)\\\"[^>]*>([^<]+)', html); "
        f"print(f'Dark web results: {{len(titles)}}'); "
        f"[print(f'  {{t.strip()}} — {{u.strip()}}') for u,t in titles[:5]]"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(dw_cmd, timeout=20):
        yield line

    # ── Stage 8: Reverse lookup links ────────────────────────────────────────
    yield "\n[8/9] Reverse lookup — open these links to identify owner..."
    yield f"TruePeopleSearch: https://www.truepeoplesearch.com/results?phoneno={digits}"
    yield f"Spokeo:           https://www.spokeo.com/phone/{digits}"
    yield f"WhitePages:       https://www.whitepages.com/phone/1-{digits}"
    yield f"NumLookup:        https://www.numlookup.com/?number={phone}"
    yield f"CallerIDTest:     https://www.calleridtest.com/{digits}"
    yield f"TrueCaller web:   https://www.truecaller.com/search/pk/{digits}"

    # ── Stage 9: Derived usernames ────────────────────────────────────────────
    yield "\n[9/9] Derived username candidates..."
    last4 = digits[-4:]
    last6 = digits[-6:]
    candidates = [last4, last6, f"user{last4}", f"user{last6}"]
    yield "Candidate usernames to cross-search:"
    for c in candidates:
        yield f"  {c}"
    yield "\nRun sherlock/maigret on these to find linked accounts."


async def profile_name(first: str, last: str, location: str = "") -> AsyncIterator[str]:
    """Name-based OSINT: web search links, theHarvester, social media."""
    full  = f"{first} {last}".strip()
    yield f"[T] Name intelligence: {full}"
    yield "─" * 50

    loc_q = f" {location}" if location else ""
    q     = (full + loc_q).replace(" ", "+")

    yield "[1/3] theHarvester — emails and subdomains..."
    cmd = (
        f"theHarvester -d '{full.replace(' ', '+')}' "
        f"-b google,bing,yahoo 2>/dev/null | head -40"
    )
    async for line in vm.run(cmd, timeout=60):
        yield line

    yield "\n[2/3] Web presence search links..."
    yield f"Google:   https://www.google.com/search?q={q}"
    yield f"LinkedIn: https://www.linkedin.com/search/results/all/?keywords={q}"
    yield f"Twitter:  https://twitter.com/search?q={q}"
    yield f"Facebook: https://www.facebook.com/search/top?q={q}"
    yield f"GitHub:   https://github.com/search?q={q}"

    yield "\n[3/3] Image reverse search (paste photo URL into these)..."
    yield "Google Images: https://images.google.com"
    yield "PimEyes:       https://pimeyes.com  (face recognition)"
    yield "Yandex:        https://yandex.com/images/"


async def profile_ip_geolocation(ip: str) -> AsyncIterator[str]:
    """Deep IP geolocation: city, ISP, org, open ports."""
    yield f"[T] IP geolocation + intel: {ip}"
    cmd = (
        f"curl -sL --connect-timeout 10 'https://ipapi.co/{ip}/json/' 2>/dev/null | "
        f"python3 -c \"import sys,json; d=json.load(sys.stdin); "
        f"[print(f'{{k}}: {{v}}') for k,v in d.items() if v]\" 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=15):
        yield line


async def phone_full_dossier(phone: str) -> AsyncIterator[str]:
    """
    Complete 4-phase person dossier starting from a phone number only.
    Phase 1: 9-stage phone intelligence
    Phase 2: Name OSINT (if name found in output)
    Phase 3: Derived username search across 3000+ platforms
    Phase 4: Breach + dark web check
    """
    phone            = phone.strip()
    digits           = re.sub(r"[^0-9]", "", phone)
    collected_name   = ""
    output_lines: list[str] = []

    yield "═" * 60
    yield f"[T] FULL PERSON DOSSIER FROM PHONE: {phone}"
    yield "═" * 60

    # ── Phase 1 ───────────────────────────────────────────────────────────────
    yield "\n◈ PHASE 1 — PHONE INTELLIGENCE"
    yield "─" * 50
    async for line in profile_phone(phone):
        output_lines.append(line)
        yield line

    # Try to extract a name from output
    for line in output_lines:
        m = re.search(r"Name:\s+(.+)", line, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            if name and name.lower() not in ("null", "none", "unknown", "n/a", ""):
                collected_name = name
                break

    # ── Phase 2 ───────────────────────────────────────────────────────────────
    if collected_name:
        yield f"\n◈ PHASE 2 — NAME OSINT (derived: {collected_name})"
        yield "─" * 50
        parts = collected_name.split(" ", 1)
        async for line in profile_name(parts[0], parts[1] if len(parts) > 1 else ""):
            yield line
    else:
        yield "\n◈ PHASE 2 — Name not found automatically."
        yield "  Tip: open the TruePeopleSearch / Spokeo links above in your browser."

    # ── Phase 3 ───────────────────────────────────────────────────────────────
    yield "\n◈ PHASE 3 — DERIVED USERNAME SEARCH"
    yield "─" * 50
    last4 = digits[-4:]
    candidates: list[str] = [last4, digits[-6:], f"user{last4}"]
    if collected_name:
        clean = collected_name.lower().replace(" ", "")
        candidates += [clean, clean + last4,
                       collected_name.lower().split()[0] + last4]

    seen: set[str] = set()
    for cand in candidates:
        # Skip purely numeric or very short candidates — too many false hits
        if len(cand) < 5 or cand.isdigit():
            yield f"[→] Skipping: {cand} (numeric/too short — not useful)"
            continue
        if cand not in seen:
            seen.add(cand)
            yield f"\n[→] Searching username: {cand}"
            async for line in profile_username(cand):
                yield line

    # ── Phase 4 ───────────────────────────────────────────────────────────────
    yield "\n◈ PHASE 4 — BREACH & DARK WEB CHECK"
    yield "─" * 50
    from intel.breach import search_paste_sites
    async for line in search_paste_sites(digits):
        yield line

    dw_cmd = (
        f"curl -sL --connect-timeout 10 "
        f"'https://ahmia.fi/search/?q={digits}' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,re; html=sys.stdin.read(); "
        f"t=re.findall(r'<h4[^>]*>.*?<a[^>]*href=\\\"([^\\\"]+)\\\"[^>]*>([^<]+)', html); "
        f"print(f'Dark web hits: {{len(t)}}'); "
        f"[print(f'  {{x[1].strip()}} — {{x[0].strip()}}') for x in t[:5]]"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(dw_cmd, timeout=20):
        yield line

    # ── Summary ───────────────────────────────────────────────────────────────
    yield "\n" + "═" * 60
    yield "[T] DOSSIER COMPLETE"
    yield f"  Phone:  {phone}"
    yield f"  Name:   {collected_name or 'Not determined'}"
    yield f"  Digits: {digits}"
    yield "═" * 60
