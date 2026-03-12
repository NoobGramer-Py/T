import os
import chromadb
from chromadb.config import Settings
from brain.core.logger import get_logger

log = get_logger("memory.store")

_DATA_DIR   = os.path.join(os.path.dirname(__file__), "..", "data", "memory")
_COLLECTION = "t_memory"

_client:     chromadb.ClientAPI | None = None
_collection: chromadb.Collection  | None = None


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is not None:
        return _collection
    os.makedirs(_DATA_DIR, exist_ok=True)
    _client = chromadb.PersistentClient(
        path=_DATA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    _collection = _client.get_or_create_collection(
        name=_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    log.info(f"memory store ready  path={_DATA_DIR}  docs={_collection.count()}")
    return _collection


def upsert(key: str, value: str) -> None:
    """Insert or update a memory entry. Key is the unique ID."""
    col = _get_collection()
    col.upsert(
        ids=[key],
        documents=[value],
        metadatas=[{"key": key}],
    )
    log.debug(f"upsert  key={key!r}")


def query(text: str, n: int = 5) -> list[dict]:
    """
    Return up to n memories most semantically relevant to text.
    Each result: {"key": str, "value": str, "distance": float}
    """
    col = _get_collection()
    if col.count() == 0:
        return []
    results = col.query(
        query_texts=[text],
        n_results=min(n, col.count()),
        include=["documents", "metadatas", "distances"],
    )
    out: list[dict] = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        out.append({"key": meta["key"], "value": doc, "distance": dist})
    return out


def delete(key: str) -> None:
    col = _get_collection()
    col.delete(ids=[key])
    log.debug(f"delete  key={key!r}")


def list_all() -> list[dict]:
    """Return all stored memories as [{key, value}]."""
    col = _get_collection()
    if col.count() == 0:
        return []
    results = col.get(include=["documents", "metadatas"])
    return [
        {"key": meta["key"], "value": doc}
        for doc, meta in zip(results["documents"], results["metadatas"])
    ]


def count() -> int:
    return _get_collection().count()
