"""
Pattern observer for T's proactive engine.
Watches conversation patterns and surfaces one-line nudges when
Abdul asks about the same topic repeatedly within a short window.
"""

import time
from collections import defaultdict
from core.logger import get_logger

log = get_logger("proactive.suggestions")

_THRESHOLD    = 3      # times asked before suggesting
_WINDOW_S     = 3600   # look-back window (1 hour)
_STOP_WORDS   = {
    "what", "how", "is", "the", "a", "an", "my", "your", "it", "this",
    "that", "can", "you", "do", "i", "me", "to", "for", "of", "in",
    "about", "tell", "show", "get", "please", "help",
}


class SuggestionEngine:
    def __init__(self) -> None:
        self._hits:   dict[str, list[float]] = defaultdict(list)
        self._fired:  set[str]               = set()

    def observe(self, user_message: str) -> str | None:
        """
        Observe one user message.
        Returns a one-line suggestion string if warranted, else None.
        """
        topic = self._extract_topic(user_message)
        if not topic:
            return None

        now  = time.time()
        hits = self._hits[topic]
        hits.append(now)
        # Trim hits outside window
        self._hits[topic] = [t for t in hits if now - t < _WINDOW_S]

        if len(self._hits[topic]) >= _THRESHOLD and topic not in self._fired:
            self._fired.add(topic)
            log.info(f"suggestion fired  topic={topic!r}")
            return f"You've asked about \"{topic}\" several times — want me to save notes on it?"

        return None

    def _extract_topic(self, msg: str) -> str | None:
        """
        Extract a normalised topic string from a message.
        Strips common question prefixes, removes stop words, returns first
        meaningful phrase (max 40 chars). Returns None if nothing useful found.
        """
        text = msg.lower().strip().rstrip("?.")
        prefixes = (
            "what is ", "what's ", "how to ", "how do i ", "can you ",
            "tell me about ", "explain ", "search for ", "find ", "look up ",
        )
        for p in prefixes:
            if text.startswith(p):
                text = text[len(p):].strip()
                break

        # Keep only meaningful words
        words = [w for w in text.split() if w not in _STOP_WORDS and len(w) > 2]
        if not words:
            return None

        topic = " ".join(words[:5])
        return topic[:40] if len(topic) >= 3 else None
