"""
Breach Monitor — checks emails/phones against breach databases.
Uses only free, no-key-required APIs.
"""

from typing import AsyncIterator
from offensive.vm_bridge import vm
from core.logger import get_logger

log = get_logger("guardian.breach_monitor")


async def check_email_breach(email: str) -> AsyncIterator[str]:
    """Check an email against free breach sources."""
    yield f"[T] Breach check: {email}"
    yield "─" * 50

    # Stage 1: breach.directory (free, no key)
    yield "[1/4] breach.directory lookup..."
    cmd1 = (
        f"curl -sL --connect-timeout 10 "
        f"'https://breachdirectory.org/api?func=auto&term={email}' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,json; "
        f"raw=sys.stdin.read(); "
        f"d=json.loads(raw) if raw.strip() else {{}}; "
        f"found=d.get('found',d.get('result',[])); "
        f"count=len(found) if isinstance(found,list) else found; "
        f"print(f'Breach results: {{count}}'); "
        f"[print(f'  {{b}}') for b in (found[:5] if isinstance(found,list) else [])]"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(cmd1, timeout=15):
        yield line

    # Stage 2: Paste site search via psbdmp
    yield "\n[2/4] Paste site search..."
    user_part = email.split("@")[0]
    cmd2 = (
        f"curl -sL --connect-timeout 10 --retry 2 "
        f"'https://psbdmp.ws/api/v3/search/{user_part}' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,json; "
        f"raw=sys.stdin.read().strip(); "
        f"d=json.loads(raw) if raw and raw[0] in '[{{' else {{}}; "
        f"data=d if isinstance(d,list) else d.get('data',[]); "
        f"print(f'Paste hits: {{len(data)}}'); "
        f"[print(f'  {{p.get(\\\"id\\\",\\\"\\\")}} — {{p.get(\\\"title\\\",\\\"no title\\\")}}') for p in data[:5]]"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(cmd2, timeout=15):
        yield line

    # Stage 3: GitHub code search
    yield "\n[3/4] GitHub code search (public repos)..."
    cmd3 = (
        f"curl -sL --connect-timeout 10 "
        f"-H 'Accept: application/vnd.github.v3+json' "
        f"'https://api.github.com/search/code?q=%22{email}%22&per_page=3' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,json; "
        f"raw=sys.stdin.read().strip(); "
        f"d=json.loads(raw) if raw else {{}}; "
        f"items=d.get('items',[])[:3]; "
        f"print(f'GitHub hits: {{d.get(\\\"total_count\\\",0)}}'); "
        f"[print(f'  {{i[\\\"repository\\\"][\\\"full_name\\\"]}}: {{i[\\\"html_url\\\"]}}') for i in items]"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(cmd3, timeout=15):
        yield line

    # Stage 4: Manual check links
    yield "\n[4/4] Manual check links (open in browser)..."
    yield f"  HaveIBeenPwned: https://haveibeenpwned.com/account/{email}"
    yield f"  DeHashed:       https://dehashed.com/search?query={email}"
    yield f"  IntelX:         https://intelx.io/?s={email}"


async def check_phone_breach(phone: str) -> AsyncIterator[str]:
    """Check a phone number against paste sites and breach sources."""
    digits = "".join(c for c in phone if c.isdigit())
    yield f"[T] Breach check: {phone}"
    yield "─" * 50

    yield "[1/3] Paste site search..."
    cmd = (
        f"curl -sL --connect-timeout 10 --retry 2 "
        f"'https://psbdmp.ws/api/v3/search/{digits}' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,json; "
        f"raw=sys.stdin.read().strip(); "
        f"d=json.loads(raw) if raw and raw[0] in '[{{' else {{}}; "
        f"data=d if isinstance(d,list) else d.get('data',[]); "
        f"print(f'Paste hits: {{len(data)}}'); "
        f"[print(f'  {{p.get(\\\"id\\\",\\\"\\\")}} — {{p.get(\\\"title\\\",\\\"no title\\\")}}') for p in data[:5]]"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=15):
        yield line

    yield "\n[2/3] GitHub code search..."
    cmd2 = (
        f"curl -sL --connect-timeout 10 "
        f"-H 'Accept: application/vnd.github.v3+json' "
        f"'https://api.github.com/search/code?q=%22{digits}%22&per_page=3' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,json; "
        f"raw=sys.stdin.read().strip(); "
        f"d=json.loads(raw) if raw else {{}}; "
        f"print(f'GitHub hits: {{d.get(\\\"total_count\\\",0)}}')"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(cmd2, timeout=15):
        yield line

    yield "\n[3/3] Manual check links..."
    yield f"  IntelX:   https://intelx.io/?s={phone}"
    yield f"  DeHashed: https://dehashed.com/search?query={phone}"


async def check_domain_breach(domain: str) -> AsyncIterator[str]:
    """Check if a domain has appeared in known breaches."""
    yield f"[T] Domain breach check: {domain}"
    yield "─" * 50

    yield "[1/3] Paste site search..."
    cmd = (
        f"curl -sL --connect-timeout 10 --retry 2 "
        f"'https://psbdmp.ws/api/v3/search/{domain}' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,json; "
        f"raw=sys.stdin.read().strip(); "
        f"d=json.loads(raw) if raw and raw[0] in '[{{' else {{}}; "
        f"data=d if isinstance(d,list) else d.get('data',[]); "
        f"print(f'Paste hits: {{len(data)}}'); "
        f"[print(f'  {{p.get(\\\"id\\\",\\\"\\\")}} — {{p.get(\\\"title\\\",\\\"no title\\\")}}') for p in data[:5]]"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=15):
        yield line

    yield "\n[2/3] GitHub search..."
    cmd2 = (
        f"curl -sL --connect-timeout 10 "
        f"-H 'Accept: application/vnd.github.v3+json' "
        f"'https://api.github.com/search/code?q=%22{domain}%22&per_page=3' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,json; raw=sys.stdin.read().strip(); "
        f"d=json.loads(raw) if raw else {{}}; "
        f"print(f'GitHub hits: {{d.get(\\\"total_count\\\",0)}}')"
        f"\" 2>/dev/null"
    )
    async for line in vm.run(cmd2, timeout=15):
        yield line

    yield "\n[3/3] Manual check links..."
    yield f"  HaveIBeenPwned: https://haveibeenpwned.com/domain/{domain}"
    yield f"  DeHashed:       https://dehashed.com/search?query={domain}"
    yield f"  IntelX:         https://intelx.io/?s={domain}"
