from .store import query


def build_context(user_message: str, profile: dict) -> str:
    """
    Build the full memory context string to inject into the system prompt.
    Combines:
      1. Profile facts (name, notes) — always included
      2. Semantically relevant ChromaDB memories — top 5 by relevance
    """
    lines: list[str] = []

    # Profile facts
    name  = profile.get("name", "").strip()
    notes = profile.get("notes", "").strip()
    if name:
        lines.append(f"User's name: {name}")
    if notes:
        lines.append(f"User notes: {notes}")

    # Semantic memory lookup
    memories = query(user_message, n=5)
    # Only include memories with cosine distance < 0.6 (reasonably relevant)
    relevant = [m for m in memories if m["distance"] < 0.6]
    for m in relevant:
        lines.append(m["value"])

    if not lines:
        return ""

    return "[MEMORY]\n" + "\n".join(f"- {l}" for l in lines) + "\n[/MEMORY]"
