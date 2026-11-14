"""Neo4j repository for MenuItem, Category, and Vector Index management."""

import json
import logging
from typing import Any

from src.exceptions import RetrievalError
from src.observability.logging import dump_json
from src.rag.graph import queries
from src.rag.graph.client import Neo4jClient
from src.schema.retrieval import ChunkRecord, EntityRecord, MenuItemRecord

logger = logging.getLogger(__name__)


def _parse_chunk_dict(raw: dict[str, Any]) -> ChunkRecord:
    data = dict(raw)
    meta = data.get("metadata")
    if isinstance(meta, str):
        try:
            data["metadata"] = json.loads(meta) if meta.strip() else {}
        except json.JSONDecodeError:
            data["metadata"] = {}
    elif not isinstance(meta, dict):
        data["metadata"] = {}
    return ChunkRecord(**data)


class Neo4jRepository:
    def __init__(self, client: Neo4jClient):
        self.client = client

    async def init_schema(self, vector_dimensions: int = 768) -> None:
        """Create uniqueness constraints and vector index on Neo4j Aura."""
        logger.info("Initializing Neo4j schema and vector index (dimensions=%d)...", vector_dimensions)
        try:
            async with self.client.session() as session:
                for constraint_query in queries.INIT_CONSTRAINTS:
                    await session.run(constraint_query)

                # Format vector dimensions if needed
                idx_query = queries.INIT_VECTOR_INDEX.replace("768", str(vector_dimensions))
                await session.run(idx_query)
            logger.info("Neo4j schema and vector index initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize Neo4j schema: %s", e)
            raise RetrievalError(f"Neo4j schema initialization failed: {e}") from e

    async def upsert_menu_item(self, item: MenuItemRecord, embedding: list[float]) -> str:
        """Upsert a MenuItem and attach to Category."""
        params = item.model_dump()
        params["embedding"] = embedding

        logger.info("STAGE Neo4jRepository.upsert_menu_item INPUT item_id=%s", item.item_id)
        try:
            async with self.client.session() as session:
                result = await session.run(queries.UPSERT_MENU_ITEM, **params)
                record = await result.single()
                item_id = record["item_id"]
                logger.info("STAGE Neo4jRepository.upsert_menu_item OUTPUT item_id=%s", item_id)
                return item_id
        except Exception as e:
            logger.error("Failed to upsert menu item %s: %s", item.item_id, e)
            raise RetrievalError(f"Upsert menu item failed: {e}") from e

    async def get_menu_item(self, item_id: str) -> MenuItemRecord | None:
        """Fetch a MenuItem by its unique item_id."""
        logger.info("STAGE Neo4jRepository.get_menu_item INPUT item_id=%s", item_id)
        try:
            async with self.client.session() as session:
                result = await session.run(queries.GET_MENU_ITEM_BY_ID, item_id=item_id)
                record = await result.single()
                if not record or not record.get("item"):
                    logger.info("STAGE Neo4jRepository.get_menu_item OUTPUT None (not found)")
                    return None
                data = dict(record["item"])
                menu_item = MenuItemRecord(**data)
                logger.info(
                    "STAGE Neo4jRepository.get_menu_item OUTPUT: %s",
                    dump_json(menu_item.model_dump(mode="json")),
                )
                return menu_item
        except Exception as e:
            logger.error("Failed to get menu item %s: %s", item_id, e)
            raise RetrievalError(f"Get menu item failed: {e}") from e

    async def find_menu_item_by_text(self, query: str) -> MenuItemRecord | None:
        """Search a MenuItem by case-insensitive exact or substring match on name_vi / name_en."""
        cleaned = query.strip()
        if not cleaned:
            return None
        logger.info("STAGE Neo4jRepository.find_menu_item_by_text INPUT query=%s", cleaned)
        try:
            async with self.client.session() as session:
                result = await session.run(queries.SEARCH_MENU_ITEM_BY_TEXT, search_text=cleaned)
                record = await result.single()
                if not record or not record.get("item"):
                    logger.info("STAGE Neo4jRepository.find_menu_item_by_text OUTPUT None")
                    return None
                menu_item = MenuItemRecord(**dict(record["item"]))
                logger.info(
                    "STAGE Neo4jRepository.find_menu_item_by_text OUTPUT: %s",
                    dump_json({"item_id": menu_item.item_id, "name_vi": menu_item.name_vi}),
                )
                return menu_item
        except Exception as e:
            logger.error("Failed to search menu item by text '%s': %s", cleaned, e)
            raise RetrievalError(f"Search menu item by text failed: {e}") from e

    async def find_menu_item_by_vector(
        self,
        embedding: list[float],
        min_score: float = 0.82,
        top_k: int = 3,
    ) -> tuple[MenuItemRecord, float] | None:
        """Search the closest MenuItem using `menu_vector_index` above `min_score`."""
        logger.info(
            "STAGE Neo4jRepository.find_menu_item_by_vector INPUT: %s",
            dump_json({"min_score": min_score, "top_k": top_k, "dim": len(embedding)}),
        )
        try:
            async with self.client.session() as session:
                result = await session.run(
                    queries.SEARCH_MENU_ITEM_BY_VECTOR,
                    embedding=embedding,
                    min_score=min_score,
                    top_k=top_k,
                )
                record = await result.single()
                if not record or not record.get("item"):
                    logger.info("STAGE Neo4jRepository.find_menu_item_by_vector OUTPUT None")
                    return None
                menu_item = MenuItemRecord(**dict(record["item"]))
                score = float(record["score"])
                logger.info(
                    "STAGE Neo4jRepository.find_menu_item_by_vector OUTPUT: %s",
                    dump_json({"item_id": menu_item.item_id, "name_vi": menu_item.name_vi, "score": score}),
                )
                return menu_item, score
        except Exception as e:
            logger.error("Failed to search menu item by vector: %s", e)
            raise RetrievalError(f"Search menu item by vector failed: {e}") from e

    async def init_chunk_schema(self, vector_dimensions: int = 768) -> None:
        """Create constraints and chunk_vector_index on Neo4j Aura."""
        logger.info("Initializing Neo4j Chunk schema and vector index (dimensions=%d)...", vector_dimensions)
        try:
            async with self.client.session() as session:
                for query in queries.INIT_CHUNK_CONSTRAINTS:
                    await session.run(query)
                idx_query = queries.INIT_CHUNK_VECTOR_INDEX.replace("768", str(vector_dimensions))
                await session.run(idx_query)
            logger.info("Neo4j Chunk schema and vector index initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize Chunk schema: %s", e)
            raise RetrievalError(f"Chunk schema initialization failed: {e}") from e

    async def upsert_chunk(self, chunk: ChunkRecord, embedding: list[float]) -> str:
        """Upsert a Chunk node with its vector embedding."""
        params = chunk.model_dump()
        params["metadata"] = dump_json(chunk.metadata)
        params["embedding"] = embedding
        logger.info("STAGE Neo4jRepository.upsert_chunk INPUT chunk_id=%s", chunk.chunk_id)
        try:
            async with self.client.session() as session:
                result = await session.run(queries.UPSERT_CHUNK, **params)
                record = await result.single()
                chunk_id = record["chunk_id"]
                logger.info("STAGE Neo4jRepository.upsert_chunk OUTPUT chunk_id=%s", chunk_id)
                return chunk_id
        except Exception as e:
            logger.error("Failed to upsert chunk %s: %s", chunk.chunk_id, e)
            raise RetrievalError(f"Upsert chunk failed: {e}") from e

    async def link_chunks_next(self, c1_id: str, c2_id: str) -> None:
        """Create a [:NEXT] relationship from chunk c1 to chunk c2."""
        logger.info("STAGE Neo4jRepository.link_chunks_next INPUT: %s -> %s", c1_id, c2_id)
        try:
            async with self.client.session() as session:
                await session.run(queries.LINK_CHUNKS_NEXT, c1_id=c1_id, c2_id=c2_id)
        except Exception as e:
            logger.error("Failed to link chunks NEXT (%s -> %s): %s", c1_id, c2_id, e)
            raise RetrievalError(f"Link chunks NEXT failed: {e}") from e

    async def link_chunk_mentions(self, chunk_id: str, entity: EntityRecord) -> None:
        """Create an Entity node if not exists and link [:MENTIONS] from Chunk."""
        params = {
            "chunk_id": chunk_id,
            "canonical_name": entity.canonical_name,
            "name": entity.name,
            "entity_type": entity.entity_type,
        }
        logger.info("STAGE Neo4jRepository.link_chunk_mentions INPUT: %s mentions %s", chunk_id, entity.canonical_name)
        try:
            async with self.client.session() as session:
                await session.run(queries.LINK_CHUNK_ENTITY_MENTIONS, **params)
        except Exception as e:
            logger.error("Failed to link chunk mentions (%s -> %s): %s", chunk_id, entity.canonical_name, e)
            raise RetrievalError(f"Link chunk mentions failed: {e}") from e

    async def search_chunks_by_vector(
        self,
        embedding: list[float],
        top_k: int = 5,
        min_score: float = 0.65,
    ) -> list[tuple[ChunkRecord, float]]:
        """Query `chunk_vector_index` for top-k Chunk nodes above `min_score`."""
        logger.info(
            "STAGE Neo4jRepository.search_chunks_by_vector INPUT: %s",
            dump_json({"top_k": top_k, "min_score": min_score}),
        )
        try:
            async with self.client.session() as session:
                result = await session.run(
                    queries.SEARCH_CHUNKS_BY_VECTOR,
                    embedding=embedding,
                    top_k=top_k,
                    min_score=min_score,
                )
                records = [r async for r in result]
                items = [
                    (_parse_chunk_dict(dict(r["chunk"])), float(r["score"]))
                    for r in records
                    if r.get("chunk")
                ]
                logger.info(
                    "STAGE Neo4jRepository.search_chunks_by_vector OUTPUT count=%d",
                    len(items),
                )
                return items
        except Exception as e:
            logger.error("Failed to search chunks by vector: %s", e)
            raise RetrievalError(f"Search chunks by vector failed: {e}") from e

    async def search_menu_items_by_vector(
        self,
        embedding: list[float],
        top_k: int = 5,
        min_score: float = 0.65,
    ) -> list[tuple[MenuItemRecord, float]]:
        """Query `menu_vector_index` for top-k MenuItem nodes above `min_score`."""
        logger.info(
            "STAGE Neo4jRepository.search_menu_items_by_vector INPUT: %s",
            dump_json({"top_k": top_k, "min_score": min_score}),
        )
        try:
            async with self.client.session() as session:
                result = await session.run(
                    queries.SEARCH_MENU_ITEMS_BY_VECTOR,
                    embedding=embedding,
                    top_k=top_k,
                    min_score=min_score,
                )
                records = [r async for r in result]
                items = [
                    (MenuItemRecord(**dict(r["item"])), float(r["score"]))
                    for r in records
                    if r.get("item")
                ]
                logger.info(
                    "STAGE Neo4jRepository.search_menu_items_by_vector OUTPUT count=%d",
                    len(items),
                )
                return items
        except Exception as e:
            logger.error("Failed to search menu items by vector: %s", e)
            raise RetrievalError(f"Search menu items by vector failed: {e}") from e

    async def expand_chunks_next(
        self, chunk_ids: list[str]
    ) -> list[tuple[ChunkRecord, str]]:
        """Expand adjacent Chunk nodes connected via [:NEXT] in either direction."""
        if not chunk_ids:
            return []
        logger.info("STAGE Neo4jRepository.expand_chunks_next INPUT count=%d", len(chunk_ids))
        try:
            async with self.client.session() as session:
                result = await session.run(queries.EXPAND_CHUNKS_NEXT, chunk_ids=chunk_ids)
                records = [r async for r in result]
                expanded = [
                    (_parse_chunk_dict(dict(r["chunk"])), str(r["parent_id"]))
                    for r in records
                    if r.get("chunk")
                ]
                logger.info("STAGE Neo4jRepository.expand_chunks_next OUTPUT count=%d", len(expanded))
                return expanded
        except Exception as e:
            logger.error("Failed to expand chunks NEXT: %s", e)
            raise RetrievalError(f"Expand chunks NEXT failed: {e}") from e

    async def expand_chunks_by_entities(
        self, chunk_ids: list[str], limit: int = 10
    ) -> list[tuple[ChunkRecord, str, str]]:
        """Expand related Chunk nodes sharing an Entity via [:MENTIONS]."""
        if not chunk_ids:
            return []
        logger.info("STAGE Neo4jRepository.expand_chunks_by_entities INPUT count=%d", len(chunk_ids))
        try:
            async with self.client.session() as session:
                result = await session.run(
                    queries.EXPAND_CHUNKS_BY_ENTITIES, chunk_ids=chunk_ids, limit=limit
                )
                records = [r async for r in result]
                expanded = [
                    (
                        _parse_chunk_dict(dict(r["chunk"])),
                        str(r["parent_id"]),
                        str(r["entity_name"]),
                    )
                    for r in records
                    if r.get("chunk")
                ]
                logger.info(
                    "STAGE Neo4jRepository.expand_chunks_by_entities OUTPUT count=%d",
                    len(expanded),
                )
                return expanded
        except Exception as e:
            logger.error("Failed to expand chunks by entities: %s", e)
            raise RetrievalError(f"Expand chunks by entities failed: {e}") from e

    async def expand_chunks_by_title_mention(
        self, chunk_ids: list[str], limit: int = 10
    ) -> list[tuple[ChunkRecord, str, int]]:
        """Bridge seed Chunks that mention a Document Chunk's title subject."""
        if not chunk_ids:
            return []
        logger.info("STAGE Neo4jRepository.expand_chunks_by_title_mention INPUT count=%d", len(chunk_ids))
        try:
            async with self.client.session() as session:
                result = await session.run(
                    queries.EXPAND_CHUNKS_BY_TITLE_MENTION, chunk_ids=chunk_ids, limit=limit
                )
                records = [r async for r in result]
                expanded = [
                    (
                        _parse_chunk_dict(dict(r["chunk"])),
                        str(r["parent_id"]),
                        int(r.get("mention_count") or 1),
                    )
                    for r in records
                    if r.get("chunk")
                ]
                logger.info(
                    "STAGE Neo4jRepository.expand_chunks_by_title_mention OUTPUT count=%d",
                    len(expanded),
                )
                return expanded
        except Exception as e:
            logger.error("Failed to expand chunks by title mention: %s", e)
            raise RetrievalError(f"Expand chunks by title mention failed: {e}") from e




