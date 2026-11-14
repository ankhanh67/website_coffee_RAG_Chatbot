"""Vector search over Neo4j Aura `chunk_vector_index` and `menu_vector_index`."""

import logging
from typing import Protocol

from src.schema.retrieval import ChunkRecord, MenuItemRecord, RetrievedItem

logger = logging.getLogger(__name__)


class VectorSearchRepository(Protocol):
    async def search_chunks_by_vector(
        self,
        embedding: list[float],
        top_k: int = 5,
        min_score: float = 0.65,
    ) -> list[tuple[ChunkRecord, float]]: ...

    async def search_menu_items_by_vector(
        self,
        embedding: list[float],
        top_k: int = 5,
        min_score: float = 0.65,
    ) -> list[tuple[MenuItemRecord, float]]: ...


def format_menu_item_text(item: MenuItemRecord) -> str:
    """Format a MenuItemRecord into a comprehensive grounded text passage."""
    prices: list[str] = []
    if item.sizes == ["Một cỡ"] and item.price_m is not None:
        prices.append(f"Một cỡ: {item.price_m:,}đ".replace(",", "."))
    else:
        if item.price_s is not None:
            prices.append(f"Size S: {item.price_s:,}đ".replace(",", "."))
        if item.price_m is not None:
            prices.append(f"Size M: {item.price_m:,}đ".replace(",", "."))
        if item.price_l is not None:
            prices.append(f"Size L: {item.price_l:,}đ".replace(",", "."))
    price_str = ", ".join(prices) if prices else "Liên hệ"
    allergens_str = ", ".join(item.allergens) if item.allergens else "không"

    return (
        f"[{item.item_id}] {item.name_vi} ({item.name_en}) - Danh mục: {item.category} ({item.category_en}). "
        f"Giá: {price_str}. Nhiệt độ: {item.temperature}. Caffeine: {item.caffeine}. "
        f"Thuần chay (vegan): {item.vegan}. Dị ứng (allergens): {allergens_str}. "
        f"Thành phần: {item.ingredients}. Mô tả: {item.description_vi} / {item.description_en}"
    )


def _normalize_chunk_source(chunk: ChunkRecord) -> str:
    if chunk.chunk_id.startswith("doc-") or chunk.source == "document":
        return "document"
    if chunk.chunk_id.startswith("faq-") or chunk.source == "faq":
        return "faq"
    return chunk.source


def chunk_to_retrieved_item(
    chunk: ChunkRecord, score: float, hop_type: str = "vector"
) -> RetrievedItem:
    meta = dict(chunk.metadata)
    if chunk.doc_id:
        meta["doc_id"] = chunk.doc_id
    if chunk.file:
        meta["file"] = chunk.file
    meta["order"] = chunk.order
    return RetrievedItem(
        node_id=chunk.chunk_id,
        source_type=_normalize_chunk_source(chunk),
        title=chunk.title,
        text=chunk.text,
        score=score,
        hop_type=hop_type,
        metadata=meta,
    )


def menu_to_retrieved_item(item: MenuItemRecord, score: float) -> RetrievedItem:
    return RetrievedItem(
        node_id=item.item_id,
        source_type="menu",
        title=f"{item.name_vi} ({item.name_en})",
        text=format_menu_item_text(item),
        score=score,
        hop_type="vector",
        metadata=item.model_dump(mode="json"),
    )


class VectorSearcher:
    def __init__(self, repository: VectorSearchRepository) -> None:
        self._repository = repository

    async def search_chunks(
        self,
        embedding: list[float],
        top_k: int = 5,
        min_score: float = 0.65,
    ) -> list[RetrievedItem]:
        pool_k = max(top_k * 5, 40)
        rows = await self._repository.search_chunks_by_vector(
            embedding=embedding, top_k=pool_k, min_score=min_score
        )
        faq_items: list[RetrievedItem] = []
        doc_items: list[RetrievedItem] = []
        for chunk, score in rows:
            item = chunk_to_retrieved_item(chunk, score, hop_type="vector")
            if item.source_type == "document":
                if len(doc_items) < top_k:
                    doc_items.append(item)
            else:
                if len(faq_items) < top_k:
                    faq_items.append(item)
        return faq_items + doc_items

    async def search_menu_items(
        self,
        embedding: list[float],
        top_k: int = 5,
        min_score: float = 0.65,
    ) -> list[RetrievedItem]:
        rows = await self._repository.search_menu_items_by_vector(
            embedding=embedding, top_k=top_k, min_score=min_score
        )
        return [menu_to_retrieved_item(item, score) for item, score in rows]

    async def search_all(
        self,
        embedding: list[float],
        top_k: int = 5,
        min_score: float = 0.65,
        include_menu: bool = True,
        include_chunks: bool = True,
    ) -> list[RetrievedItem]:
        results: list[RetrievedItem] = []
        if include_chunks:
            results.extend(
                await self.search_chunks(embedding=embedding, top_k=top_k, min_score=min_score)
            )
        if include_menu:
            results.extend(
                await self.search_menu_items(embedding=embedding, top_k=top_k, min_score=min_score)
            )
        return results
