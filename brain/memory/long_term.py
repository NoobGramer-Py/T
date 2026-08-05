"""
Long-Term Knowledge & Semantic Memory Layer for T AI OS.
Provides persistent knowledge storage, indexing interface, and database adapter compatibility.
"""

from typing import List, Dict, Any, Optional
from brain.logging.logger import get_logger

log = get_logger("memory.long_term")


class LongTermMemory:
    """Interface for persistent knowledge indexing, semantic retrieval, and storage."""

    def __init__(self) -> None:
        self._documents: List[Dict[str, Any]] = []

    async def store_doc(self, title: str, content: str, tags: Optional[List[str]] = None) -> str:
        """Stores a document entry in long-term knowledge."""
        doc_id = f"doc_{len(self._documents) + 1}"
        entry = {
            "id": doc_id,
            "title": title,
            "content": content,
            "tags": tags or [],
        }
        self._documents.append(entry)
        log.info(f"Stored long-term knowledge document '{title}' (ID: {doc_id})")
        return doc_id

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Simple keyword/semantic search adapter over long-term knowledge documents."""
        q_lower = query.lower()
        results = []
        for doc in self._documents:
            if q_lower in doc["title"].lower() or q_lower in doc["content"].lower():
                results.append(doc)
            if len(results) >= limit:
                break
        return results


long_term_memory = LongTermMemory()
