"""
Contextual wordlist generator for T's attack system.
Generates targeted password candidates from site intelligence:
domain name, usernames, emails, detected tech stack, and location signals.
No static list — every wordlist is built from what was found on the target.
"""

import re
from itertools import product


def generate(
    domain:    str = "",
    usernames: list[str] = None,
    emails:    list[str] = None,
    keywords:  list[str] = None,
    year_range: tuple[int, int] = (2022, 2026),
) -> list[str]:
    """
    Build a contextual password list from target intelligence.
    Returns deduplicated, ordered list — most likely passwords first.
    """
    seeds = set()

    # Extract seeds from domain
    if domain:
        clean = re.sub(r'\.(com|net|org|io|co|pk|uk|us|info|shop).*$', '', domain.lower())
        clean = re.sub(r'^(www\.|https?://)', '', clean)
        parts = re.split(r'[.\-_]', clean)
        for p in parts:
            if len(p) >= 3:
                seeds.add(p)
        seeds.add(clean.replace("-", "").replace("_", ""))
        seeds.add(clean)

    # Extract seeds from usernames
    for u in (usernames or []):
        clean = u.lower().replace("-com", "").replace("@gmail", "")
        parts = re.split(r'[.\-_@]', clean)
        for p in parts:
            if len(p) >= 3:
                seeds.add(p)
        seeds.add(clean)

    # Extract seeds from emails
    for e in (emails or []):
        local = e.split("@")[0].lower()
        parts = re.split(r'[.\-_+]', local)
        for p in parts:
            if len(p) >= 3:
                seeds.add(p)
        seeds.add(local)

    # Extra keywords
    for k in (keywords or []):
        seeds.add(k.lower())

    seeds.discard("")

    passwords = []

    # Tier 1 — raw seeds and simple capitalizations (most likely)
    for s in seeds:
        passwords += [
            s,
            s.capitalize(),
            s.upper(),
        ]

    # Tier 2 — seeds with common suffixes
    common_suffixes = ["123", "1234", "12345", "123456", "1", "!", "@", "#",
                       "@123", "@1234", "!", "!1", "123!", "321"]
    for s in seeds:
        for suf in common_suffixes:
            passwords.append(s + suf)
            passwords.append(s.capitalize() + suf)

    # Tier 3 — seeds with years
    for s in seeds:
        for year in range(year_range[0], year_range[1] + 1):
            passwords += [
                f"{s}{year}",
                f"{s.capitalize()}{year}",
                f"{s}@{year}",
                f"{s.capitalize()}@{year}",
            ]

    # Tier 4 — seeds with common patterns
    patterns = [
        lambda s: s + "admin",
        lambda s: s + "_admin",
        lambda s: "admin" + s,
        lambda s: s + "wp",
        lambda s: s + "pass",
        lambda s: s + "password",
        lambda s: s + "@wordpress",
        lambda s: s + "wordpress",
    ]
    for s in seeds:
        for p in patterns:
            passwords.append(p(s))
            passwords.append(p(s.capitalize()))

    # Tier 5 — universal common passwords (always include as fallback)
    universal = [
        "admin", "password", "123456", "admin123", "letmein", "welcome",
        "password1", "Password1", "Password123", "Admin@123", "Admin123",
        "wordpress", "Wordpress1", "changeme", "qwerty", "111111",
        "iloveyou", "sunshine", "master", "dragon", "shadow",
        "pakistan", "Pakistan", "Pakistan123", "lahore", "Lahore123",
        "karachi", "Karachi123", "islamabad", "Islamabad123",
    ]
    passwords += universal

    # Deduplicate preserving order, filter out too-short or too-long
    seen = set()
    result = []
    for p in passwords:
        if p not in seen and 4 <= len(p) <= 32:
            seen.add(p)
            result.append(p)

    return result
