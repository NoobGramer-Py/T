"""
Dark web intelligence module for T.
Searches Tor network via the attack VM (which runs Tor).
Monitors paste sites, searches breach DBs, enumerates known .onion services.
"""

from typing import AsyncIterator
from offensive.vm_bridge import vm
from core.logger import get_logger

log = get_logger("intel.darkweb")

# Known .onion search engines and directories
ONION_SEARCH_ENGINES = [
    ("Ahmia",     "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/search/?q="),
    ("Torch",     "http://torchdeedp3i2jigzjdmfpn5ttjhthh5wbmda2rr3jvqjg5p77c54dqd.onion/search?query="),
    ("Haystak",   "http://haystak5njsmn2hqkewecpaxetahtwhsbsa64jom2k22z5afxhnpxfid.onion/search?q="),
]

# Known .onion sites by category (for enumeration)
KNOWN_ONIONS = {
    "search":   ["ahmia.fi", "torch search", "haystak"],
    "paste":    ["zerobin.onion", "privatebin.onion"],
    "markets":  ["(monitoring only — no interaction)"],
    "intel":    ["intelx.io (clearnet dark web search)"],
}


async def setup_tor_proxy(client=None) -> AsyncIterator[str]:
    """Ensure Tor is running on the VM and configure proxychains."""
    yield "[T] Setting up Tor proxy on VM..."

    cmd = (
        "which tor 2>/dev/null || sudo apt install -y tor -q; "
        "sudo systemctl start tor 2>/dev/null || tor --RunAsDaemon 1 2>/dev/null; "
        "sleep 3; "
        "curl --socks5 127.0.0.1:9050 --connect-timeout 10 "
        "-sL 'https://check.torproject.org/api/ip' 2>/dev/null | "
        "python3 -c \"import sys,json; d=json.load(sys.stdin); "
        "print('Tor IP:', d.get('IP','?'), '| Is Tor:', d.get('IsTor','?'))\" 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=30):
        yield line


async def tor_search(query: str) -> AsyncIterator[str]:
    """Search Tor network via Ahmia (clearnet Tor search index)."""
    yield f"[T] Dark web search: {query}"

    # Use Ahmia clearnet index (doesn't require Tor)
    encoded = query.replace(" ", "+")
    cmd = (
        f"curl -sL --connect-timeout 10 "
        f"'https://ahmia.fi/search/?q={encoded}' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,re; "
        f"html=sys.stdin.read(); "
        f"titles=re.findall(r'<h4[^>]*>.*?<a[^>]*href=\\\"([^\\\"]+)\\\"[^>]*>([^<]+)', html); "
        f"descs=re.findall(r'<p class=\\\"description\\\"[^>]*>([^<]+)', html); "
        f"for i,(url,title) in enumerate(titles[:10]): "
        f"  desc=descs[i] if i<len(descs) else ''; "
        f"  print(f'{{title.strip()}}\\n  {{url.strip()}}\\n  {{desc.strip()}}\\n')\""
        f" 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=20):
        yield line


async def onion_search_via_tor(query: str) -> AsyncIterator[str]:
    """Search .onion sites directly via Tor (requires Tor running on VM)."""
    yield f"[T] .onion search via Tor: {query}"

    encoded = query.replace(" ", "%20")
    engine_url = f"http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/search/?q={encoded}"

    cmd = (
        f"proxychains -q curl --socks5-hostname 127.0.0.1:9050 "
        f"--connect-timeout 30 -sL '{engine_url}' 2>/dev/null | "
        f"python3 -c \""
        f"import sys,re; html=sys.stdin.read(); "
        f"results=re.findall(r'<a[^>]*href=\\\"(http://[a-z2-7]{{16,56}}\\.onion[^\\\"]*)\\\">([^<]+)', html); "
        f"[print(f'{{title.strip()}}\\n  {{url}}\\n') for url,title in results[:15]]\""
        f" 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=60):
        yield line


async def intelx_search(query: str, api_key: str = "") -> AsyncIterator[str]:
    """
    Search IntelligenceX (intelx.io) — indexes dark web, Tor, I2P, paste sites.
    Has a free tier with limited results.
    """
    yield f"[T] IntelX search: {query}"

    if api_key:
        # Start search
        cmd = (
            f"curl -sL -X POST 'https://2.intelx.io/intelligent/search' "
            f"-H 'x-key: {api_key}' "
            f"-H 'Content-Type: application/json' "
            f"-d '{{\"term\":\"{query}\",\"buckets\":[],\"lookuplevel\":0,\"maxresults\":10,\"timeout\":10,\"datefrom\":\"\",\"dateto\":\"\",\"sort\":4,\"media\":0,\"terminate\":[]}}' "
            f"2>/dev/null"
        )
        async for line in vm.run(cmd, timeout=20):
            yield line
    else:
        yield "(No IntelX API key set. Get a free key at https://intelx.io)"
        yield "Searching clearnet index instead..."
        async for line in tor_search(query):
            yield line


async def monitor_paste_sites(keyword: str, duration_s: int = 30) -> AsyncIterator[str]:
    """Monitor paste sites for a keyword appearing in new pastes."""
    yield f"[T] Paste site monitor: {keyword} (for {duration_s}s)"

    cmd = (
        f"timeout {duration_s} bash -c \""
        f"while true; do "
        f"  RESULT=$(curl -sL --connect-timeout 5 "
        f"  'https://psbdmp.ws/api/v3/search/{keyword}' 2>/dev/null | "
        f"  python3 -c \\\"import sys,json; "
        f"  d=json.load(sys.stdin); "
        f"  data=d if isinstance(d,list) else d.get('data',[]); "
        f"  [print(f\\\\\\\"PASTE: {{p.get('id')}} | {{p.get('title')}} | https://pastebin.com/{{p.get('id')}}\\\\\\\") for p in (data[:3] if data else [])]\\\"); "
        f"  [ -n \\\"$RESULT\\\" ] && echo \\\"$RESULT\\\"; "
        f"  sleep 5; "
        f"done\" 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=duration_s + 5):
        yield line


async def darkweb_email_search(email: str) -> AsyncIterator[str]:
    """Search dark web for email address appearances."""
    yield f"[T] Dark web email search: {email}"

    yield "[1/3] Ahmia search..."
    async for line in tor_search(f'"{email}"'):
        yield line

    yield "\n[2/3] Paste site search..."
    encoded = email.replace("@", "%40")
    cmd = (
        f"curl -sL 'https://psbdmp.ws/api/v3/search/{encoded}' 2>/dev/null | "
        f"python3 -c \"import sys,json; "
        f"d=json.load(sys.stdin); "
        f"data=d if isinstance(d,list) else d.get('data',[]); "
        f"[print(f\\\"{{p.get('id')}} | {{p.get('title')}} | https://pastebin.com/{{p.get('id')}}\\\") for p in (data[:10] if data else [])]\""
        f" 2>/dev/null"
    )
    async for line in vm.run(cmd, timeout=15):
        yield line

    yield "\n[3/3] GitHub leak search..."
    cmd2 = (
        f"curl -sL -H 'Accept: application/vnd.github.v3+json' "
        f"'https://api.github.com/search/code?q=%22{email}%22&per_page=5' 2>/dev/null | "
        f"python3 -c \"import sys,json; "
        f"d=json.load(sys.stdin); "
        f"items=d.get('items',[])[:5]; "
        f"[print(f\\\"{{i['repository']['full_name']}}: {{i['path']}} — {{i['html_url']}}\\\") for i in items]\""
        f" 2>/dev/null"
    )
    async for line in vm.run(cmd2, timeout=15):
        yield line


async def list_known_onions() -> AsyncIterator[str]:
    """List known .onion sites by category."""
    yield "[T] Known .onion directory"
    yield "─" * 50
    for category, sites in KNOWN_ONIONS.items():
        yield f"\n[{category.upper()}]"
        for site in sites:
            yield f"  • {site}"
