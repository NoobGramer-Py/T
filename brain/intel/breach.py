"""
Breach data intelligence module for T.
Checks email/domain/username against known breach databases.
Generates targeted wordlists from breach data for credential stuffing simulation.
"""

import re
from typing import AsyncIterator
from offensive.vm_bridge import vm
from core.logger import get_logger

log = get_logger("intel.breach")


async def check_hibp(email: str, api_key: str = "") -> AsyncIterator[str]:
    """Check HaveIBeenPwned for email breach data."""
    yield f"[T] HIBP breach check: {email}"

    if api_key:
        cmd = (
            f"curl -sL -H 'hibp-api-key: {api_key}' "
            f"-H 'user-agent: T-OSINT' "
            f"'https://haveibeenpwned.com/api/v3/breachedaccount/{email}' 2>/dev/null | "
            f"python3 -c \"import sys,json; "
            f"data=json.load(sys.stdin); "
            f"[print(f\\\"Breach: {{b['Name']}} ({b['BreachDate']}) — {{b['DataClasses']}}\\\") for b in data]\" 2>/dev/null"
        )
    else:
        cmd = (
            f"echo 'No HIBP API key set. Set hibpKey in Settings > Profile.' && "
            f"echo 'Get a free key at: https://haveibeenpwned.com/API/Key'"
        )
    async for line in vm.run(cmd, timeout=20):
        yield line


async def check_dehashed(query: str, query_type: str = "email") -> AsyncIterator[str]:
    """
    Search DeHashed for leaked credentials.
    query_type: email | username | password | name | domain
    """
    yield f"[T] DeHashed search: {query_type}={query}"
    yield "(Requires DeHashed API credentials — set in environment or T config)"
    cmd = (
        f"curl -sL -H 'Accept: application/json' "
        f"'https://api.dehashed.com/search?query={query_type}:{query}&size=10' 2>/dev/null | "
        f"python3 -c \"import sys,json; "
        f"d=json.load(sys.stdin); "
        f"entries=d.get('entries',[]) or []; "
        f"[print(f\\\"{{e.get('email','')}} | {{e.get('username','')}} | {{e.get('password','')}} | {{e.get('database_name','')}}\\\") for e in entries[:20]]\" 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=20):
        yield line


async def search_paste_sites(query: str) -> AsyncIterator[str]:
    """Search Pastebin, GitHub, and paste sites for leaked data."""
    yield f"[T] Paste site search: {query}"

    sites = [
        f"https://psbdmp.ws/api/search/{query}",
        f"https://pastebin.com/search?q={query}",
    ]

    yield "[1/2] GitHub code search (public repos)..."
    cmd = (
        f"curl -sL -H 'Accept: application/vnd.github.v3+json' "
        f"'https://api.github.com/search/code?q={query}&per_page=5' 2>/dev/null | "
        f"python3 -c \"import sys,json; "
        f"d=json.load(sys.stdin); "
        f"items=d.get('items',[])[:5]; "
        f"[print(f\\\"{{i['repository']['full_name']}}: {{i['path']}} — {{i['html_url']}}\\\") for i in items]\" 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=15):
        yield line

    yield "\n[2/2] Pastebin dump search..."
    cmd2 = (
        f"curl -sL 'https://psbdmp.ws/api/v3/search/{query}' 2>/dev/null | "
        f"python3 -c \"import sys,json; "
        f"d=json.load(sys.stdin); "
        f"data=d if isinstance(d,list) else d.get('data',[])[:5]; "
        f"[print(f\\\"{{p.get('id','')}} — {{p.get('title','')}}: https://pastebin.com/{{p.get('id','')}}\\\") for p in data[:5]]\" 2>/dev/null"
    )
    async for line in vm.run(cmd2, timeout=15):
        yield line


async def search_combo_lists(query: str, combo_dir: str = "/usr/share/wordlists") -> AsyncIterator[str]:
    """Search local combo lists / breach dumps on VM for a query string."""
    yield f"[T] Combo list search: {query}"
    cmd = (
        f"find {combo_dir} -name '*.txt' 2>/dev/null | "
        f"xargs grep -l '{query}' 2>/dev/null | head -5 | "
        f"xargs -I{{}} grep '{query}' {{}} 2>/dev/null | head -20"
    )
    async for line in vm.run(cmd, timeout=30):
        yield line


async def gen_targeted_wordlist(target_info: dict) -> AsyncIterator[str]:
    """
    Generate a targeted password wordlist from personal info.
    Uses CUPP (Common User Passwords Profiler).
    target_info: {first, last, nickname, birthdate, partner, child, pet, keywords}
    """
    yield "[T] Generating targeted wordlist with CUPP..."

    first    = target_info.get("first", "")
    last     = target_info.get("last", "")
    nickname = target_info.get("nickname", "")
    bdate    = target_info.get("birthdate", "")   # DDMMYYYY
    partner  = target_info.get("partner", "")
    child    = target_info.get("child", "")
    pet      = target_info.get("pet", "")
    company  = target_info.get("company", "")
    keywords = target_info.get("keywords", "")

    # CUPP interactive mode via stdin
    answers = "\n".join([
        first, last, nickname, bdate,
        partner, "", "",   # partner dob, partner nick
        child, "", "",     # child dob, child nick
        pet, company,
        "y",               # add special chars
        "y",               # add random numbers
        "y",               # leet mode
        keywords,
        "n",               # no more keywords
    ])

    cmd = (
        f"echo '{answers}' | cupp -i 2>/dev/null; "
        f"ls *.txt 2>/dev/null | head -3 | "
        f"xargs -I{{}} sh -c 'echo \"Generated: {{}} ($(wc -l < {{}}) passwords)\"'"
    )
    async for line in vm.run(cmd, timeout=60):
        yield line


async def password_pattern_analysis(password_list: list[str]) -> AsyncIterator[str]:
    """Analyse a list of known passwords to find patterns."""
    yield "[T] Password pattern analysis..."

    if not password_list:
        yield "[ERROR] No passwords provided"
        return

    # Write passwords to temp file and analyse
    pw_str = "\\n".join(password_list[:500])
    cmd = (
        f"printf '{pw_str}\\n' > /tmp/pw_analysis.txt && "
        f"echo 'Total: '$(wc -l < /tmp/pw_analysis.txt) && "
        f"echo 'Average length: '$(awk '{{sum+=length($0)}} END {{print sum/NR}}' /tmp/pw_analysis.txt) && "
        f"echo 'Top patterns:' && "
        f"cat /tmp/pw_analysis.txt | sed 's/[0-9]/N/g;s/[a-zA-Z]/L/g;s/[^LN]/S/g' | "
        f"sort | uniq -c | sort -rn | head -10"
    )
    async for line in vm.run(cmd, timeout=15):
        yield line


async def check_password_breach(password: str) -> AsyncIterator[str]:
    """
    Check if a password has appeared in known breaches (k-anonymity HIBP API).
    Only sends first 5 chars of SHA1 hash — password never leaves machine.
    """
    import hashlib
    sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
    prefix = sha1[:5]
    suffix = sha1[5:]

    yield f"[T] Password breach check (k-anonymity)..."
    yield f"SHA1 prefix: {prefix}*** (password not transmitted)"

    cmd = (
        f"curl -sL 'https://api.pwnedpasswords.com/range/{prefix}' 2>/dev/null | "
        f"grep -i '{suffix}' | "
        f"python3 -c \"import sys; "
        f"line=sys.stdin.read().strip(); "
        f"count=line.split(':')[-1] if ':' in line else '0'; "
        f"print(f'FOUND IN {{count}} BREACHES' if count!='0' else 'NOT FOUND in known breaches')\""
    )
    async for line in vm.run(cmd, timeout=10):
        yield line
