"""
Web intelligence integration for T.
Search: DuckDuckGo (no API key required)
Weather: Open-Meteo (no API key required)
News: GNews public API (no key) or RSS fallback
URL: fetch and summarize page content
"""

import httpx
import re
from datetime import datetime
from core.logger import get_logger

log = get_logger("integrations.web")

_TIMEOUT  = httpx.Timeout(15.0)
_HEADERS  = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


async def web_search(query: str, max_results: int = 6) -> str:
    """
    Search DuckDuckGo and return top results.
    No API key. Uses DDG's HTML endpoint + lite JSON API.
    """
    try:
        # DuckDuckGo instant answer API
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as c:
            r = await c.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            )
        data = r.json()

        results = []

        # Abstract (Wikipedia-style answer)
        if data.get("AbstractText"):
            results.append(f"[Summary] {data['AbstractText']}")
            if data.get("AbstractURL"):
                results.append(f"Source: {data['AbstractURL']}")

        # Instant answer
        if data.get("Answer"):
            results.append(f"[Answer] {data['Answer']}")

        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                text = topic["Text"][:200]
                url  = topic.get("FirstURL", "")
                results.append(f"• {text}\n  {url}")

        if not results:
            # Fallback: DDG HTML scrape
            results = await _ddg_html_search(query, max_results)

        if not results:
            return f"No results found for: {query}"

        return f"Search: {query}\n\n" + "\n\n".join(results[:max_results])

    except Exception as e:
        log.warning(f"web_search error: {e}")
        return f"[ERROR] Search failed: {e}"


async def _ddg_html_search(query: str, max_results: int) -> list[str]:
    """Fallback: scrape DuckDuckGo HTML results."""
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            headers=_HEADERS,
            follow_redirects=True,
        ) as c:
            r = await c.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
            )
        body = r.text

        # Extract result snippets
        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</a>',
            body, re.DOTALL
        )
        titles = re.findall(
            r'class="result__a"[^>]*>(.*?)</a>',
            body, re.DOTALL
        )
        urls = re.findall(
            r'class="result__url"[^>]*>(.*?)</span>',
            body, re.DOTALL
        )

        results = []
        for i in range(min(max_results, len(snippets))):
            title   = re.sub(r'<[^>]+>', '', titles[i]).strip()   if i < len(titles)   else ""
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip() if i < len(snippets) else ""
            url     = urls[i].strip()                             if i < len(urls)     else ""
            if snippet:
                results.append(f"• {title}\n  {snippet}\n  {url}")

        return results
    except Exception:
        return []


async def get_weather(location: str) -> str:
    """
    Get current weather + 3-day forecast for any location.
    Uses Open-Meteo geocoding + weather APIs. No API key required.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            # Step 1: geocode location
            geo = await c.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": location, "count": 1, "language": "en", "format": "json"},
            )
            geo_data = geo.json()
            if not geo_data.get("results"):
                return f"Location not found: {location}"

            place = geo_data["results"][0]
            lat   = place["latitude"]
            lon   = place["longitude"]
            name  = place.get("name", location)
            country = place.get("country", "")

            # Step 2: weather
            weather = await c.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude":              lat,
                    "longitude":             lon,
                    "current":               "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,apparent_temperature",
                    "daily":                 "temperature_2m_max,temperature_2m_min,weather_code,precipitation_sum",
                    "timezone":              "auto",
                    "forecast_days":         4,
                    "wind_speed_unit":       "kmh",
                    "temperature_unit":      "celsius",
                },
            )
            w = weather.json()

        cur    = w["current"]
        daily  = w["daily"]
        desc   = _wmo_description(cur["weather_code"])

        lines = [
            f"Weather — {name}, {country}",
            f"",
            f"Now:        {cur['temperature_2m']}°C (feels {cur['apparent_temperature']}°C)  {desc}",
            f"Humidity:   {cur['relative_humidity_2m']}%",
            f"Wind:       {cur['wind_speed_10m']} km/h",
            f"",
            "3-Day Forecast:",
        ]

        for i in range(1, 4):
            date  = daily["time"][i]
            hi    = daily["temperature_2m_max"][i]
            lo    = daily["temperature_2m_min"][i]
            rain  = daily["precipitation_sum"][i]
            cond  = _wmo_description(daily["weather_code"][i])
            lines.append(f"  {date}  {lo}–{hi}°C  {cond}  rain={rain}mm")

        return "\n".join(lines)

    except Exception as e:
        log.warning(f"get_weather error: {e}")
        return f"[ERROR] Weather fetch failed: {e}"


async def fetch_url(url: str, max_chars: int = 3000) -> str:
    """
    Fetch a URL and return readable text content (strips HTML tags).
    """
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            headers=_HEADERS,
            follow_redirects=True,
        ) as c:
            r = await c.get(url)

        ct = r.headers.get("content-type", "")
        if "json" in ct:
            return r.text[:max_chars]

        html = r.text

        # Strip scripts and styles
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>',  '', html, flags=re.DOTALL | re.IGNORECASE)

        # Extract title
        title_m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        title   = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else ""

        # Strip remaining tags
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()

        header = f"URL: {url}\nTitle: {title}\nStatus: {r.status_code}\n\n"
        return header + text[:max_chars]

    except Exception as e:
        log.warning(f"fetch_url error: {e}")
        return f"[ERROR] Fetch failed: {e}"


async def get_news(topic: str = "", max_results: int = 5) -> str:
    """
    Get latest news via DuckDuckGo news search.
    topic: search term, empty = top headlines
    """
    query = f"{topic} news" if topic else "top news today"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as c:
            r = await c.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1"},
            )
        data = r.json()

        results = []
        for item in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(item, dict) and item.get("Text"):
                text = item["Text"][:250]
                url  = item.get("FirstURL", "")
                results.append(f"• {text}\n  {url}")

        if not results:
            # Fallback to search
            return await web_search(query, max_results)

        header = f"News: {topic or 'top headlines'}\n\n"
        return header + "\n\n".join(results)

    except Exception as e:
        log.warning(f"get_news error: {e}")
        return f"[ERROR] News fetch failed: {e}"


# ─── WMO weather code descriptions ────────────────────────────────────────────

def _wmo_description(code: int) -> str:
    table = {
        0:  "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Icy fog",
        51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
        61: "Light rain", 63: "Rain", 65: "Heavy rain",
        71: "Light snow", 73: "Snow", 75: "Heavy snow",
        80: "Light showers", 81: "Showers", 82: "Heavy showers",
        95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Heavy thunderstorm + hail",
    }
    return table.get(code, f"code={code}")
