"""Neo4j repository for MenuItem, Category, and Vector Index management."""

import logging

from src.exceptions import RetrievalError
from src.observability.logging import dump_json
from src.rag.graph import queries
from src.rag.graph.client import Neo4jClient
from src.schema.retrieval import MenuItemRecord

logger = logging.getLogger(__name__)


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
                result = await session.run(queries.SEARCH_MENU_ITEM_BY_TEXT, query=cleaned)
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

