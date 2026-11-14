"""Semantic Cache for Consultant and FAQ responses (never caches Order stateful turns)."""

import logging
import math
import time
from dataclasses import dataclass
from typing import Protocol

from src.observability.logging import dump_json
from src.schema.router import RouterAction

logger = logging.getLogger(__name__)

CACHEABLE_ACTIONS: frozenset[RouterAction] = frozenset({
    RouterAction.CONSULTANT,
    RouterAction.FAQ,
})


class CacheEmbeddingProvider(Protocol):
    async def get_embedding(self, text: str) -> list[float]: ...


@dataclass
class SemanticCacheEntry:
    query: str
    embedding: list[float]
    action: RouterAction
    reply: str
    created_at: float


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two dense float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticCache:
    """In-memory semantic cache with cosine similarity matching and TTL expiration."""

    def __init__(
        self,
        embeddings_client: CacheEmbeddingProvider,
        similarity_threshold: float = 0.92,
        ttl_seconds: float = 3600.0,
        max_entries: int = 500,
    ) -> None:
        self._embeddings = embeddings_client
        self._similarity_threshold = similarity_threshold
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._entries: list[SemanticCacheEntry] = []

    def is_cacheable(self, action: RouterAction) -> bool:
        return action in CACHEABLE_ACTIONS

    def _evict_expired(self, now: float) -> None:
        self._entries = [
            entry for entry in self._entries if (now - entry.created_at) < self._ttl_seconds
        ]

    async def lookup(self, query: str) -> tuple[SemanticCacheEntry, float] | None:
        """Find the highest-scoring cached entry above `similarity_threshold`."""
        cleaned = query.strip()
        if not cleaned or not self._entries:
            return None

        now = time.monotonic()
        self._evict_expired(now)
        if not self._entries:
            return None

        # Exact normalized text match shortcut
        lowered = cleaned.lower()
        for entry in self._entries:
            if entry.query.lower() == lowered:
                logger.info(
                    "STAGE SemanticCache.lookup EXACT HIT: %s",
                    dump_json({"query": cleaned, "action": entry.action}),
                )
                return entry, 1.0

        query_vec = await self._embeddings.get_embedding(cleaned)
        best_entry: SemanticCacheEntry | None = None
        best_score = -1.0

        for entry in self._entries:
            score = cosine_similarity(query_vec, entry.embedding)
            if score > best_score:
                best_score = score
                best_entry = entry

        if best_entry is not None and best_score >= self._similarity_threshold:
            logger.info(
                "STAGE SemanticCache.lookup SEMANTIC HIT: %s",
                dump_json(
                    {
                        "query": cleaned,
                        "matched_query": best_entry.query,
                        "score": round(best_score, 4),
                        "action": best_entry.action,
                    }
                ),
            )
            return best_entry, best_score

        return None

    async def store(self, query: str, action: RouterAction, reply: str) -> None:
        """Store a response in cache only if `action` is cacheable (CONSULTANT or FAQ)."""
        cleaned = query.strip()
        if not cleaned or not reply.strip() or not self.is_cacheable(action):
            return

        now = time.monotonic()
        self._evict_expired(now)

        embedding = await self._embeddings.get_embedding(cleaned)
        if len(self._entries) >= self._max_entries:
            self._entries.pop(0)

        self._entries.append(
            SemanticCacheEntry(
                query=cleaned,
                embedding=embedding,
                action=action,
                reply=reply,
                created_at=now,
            )
        )
        logger.info(
            "STAGE SemanticCache.store SAVED: %s",
            dump_json({"query": cleaned, "action": action, "total_entries": len(self._entries)}),
        )

    def clear(self) -> None:
        self._entries.clear()
