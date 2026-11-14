"""Graph traversal search over Neo4j Aura (`[:NEXT]` window expansion and `[:MENTIONS]` entity hops)."""

import logging
from typing import Protocol

from src.rag.retrieval.vector_search import chunk_to_retrieved_item
from src.schema.retrieval import ChunkRecord, RetrievedItem

logger = logging.getLogger(__name__)


class GraphSearchRepository(Protocol):
    async def expand_chunks_next(
        self, chunk_ids: list[str]
    ) -> list[tuple[ChunkRecord, str]]: ...

    async def expand_chunks_by_entities(
        self, chunk_ids: list[str], limit: int = 10
    ) -> list[tuple[ChunkRecord, str, str]]: ...


class GraphSearcher:
    def __init__(
        self,
        repository: GraphSearchRepository,
        next_decay: float = 0.92,
        entity_decay: float = 0.88,
    ) -> None:
        self._repository = repository
        self._next_decay = next_decay
        self._entity_decay = entity_decay

    async def expand(
        self,
        seed_items: list[RetrievedItem],
        max_seeds: int = 5,
        entity_limit: int = 6,
    ) -> list[RetrievedItem]:
        """Expand top seed chunks via `[:NEXT]`, `[:MENTIONS]`, and title-mention bridging."""
        chunk_seeds = [item for item in seed_items if item.source_type != "menu"][:max_seeds]
        if not chunk_seeds:
            return []

        parent_scores: dict[str, float] = {item.node_id: item.score for item in chunk_seeds}
        seed_ids = list(parent_scores.keys())

        expanded: list[RetrievedItem] = []

        # 1. Expand adjacent document chunks along [:NEXT]
        next_rows = await self._repository.expand_chunks_next(seed_ids)
        for chunk, parent_id in next_rows:
            base_score = parent_scores.get(parent_id, 0.70)
            item = chunk_to_retrieved_item(
                chunk,
                score=round(base_score * self._next_decay, 4),
                hop_type="next",
            )
            item.metadata["parent_id"] = parent_id
            expanded.append(item)

        # 2. Expand related chunks sharing an Entity via [:MENTIONS]
        entity_rows = await self._repository.expand_chunks_by_entities(
            seed_ids, limit=entity_limit
        )
        for chunk, parent_id, entity_name in entity_rows:
            base_score = parent_scores.get(parent_id, 0.70)
            item = chunk_to_retrieved_item(
                chunk,
                score=round(base_score * self._entity_decay, 4),
                hop_type="entity",
            )
            item.metadata["parent_id"] = parent_id
            item.metadata["shared_entity"] = entity_name
            expanded.append(item)

        # 3. Bridge FAQ/seed chunks that mention a Document chunk's title subject
        title_expand_fn = getattr(self._repository, "expand_chunks_by_title_mention", None)
        if callable(title_expand_fn):
            title_rows = await title_expand_fn(seed_ids, limit=max(entity_limit, 10))
            for row in title_rows:
                chunk, parent_id = row[0], row[1]
                mention_count = int(row[2]) if len(row) > 2 else 1
                base_score = parent_scores.get(parent_id, 0.70)
                multi_seed_boost = min(0.06, 0.02 * (mention_count - 1))
                item = chunk_to_retrieved_item(
                    chunk,
                    score=round(min(1.0, base_score * self._entity_decay + multi_seed_boost), 4),
                    hop_type="entity",
                )
                item.metadata["parent_id"] = parent_id
                expanded.append(item)

        return expanded
