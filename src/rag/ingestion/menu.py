"""Ingest menu items from data/raw/menu/menu.csv into Neo4j Aura with vector embeddings."""

import csv
import logging
from pathlib import Path

from src.observability.logging import dump_json
from src.rag.embeddings import EmbeddingsClient
from src.rag.graph.repository import Neo4jRepository
from src.rag.ingestion.base import BaseIngestor
from src.schema.retrieval import MenuItemRecord

logger = logging.getLogger(__name__)


def build_menu_item_embedding_text(item: MenuItemRecord) -> str:
    """Construct a dense semantic description for embedding."""
    allergens_str = ", ".join(item.allergens) if item.allergens else "không"
    parts = [
        f"Món: {item.name_vi} ({item.name_en})",
        f"Danh mục: {item.category}",
        f"Nhiệt độ: {item.temperature}, Caffein: {item.caffeine}, Thuần chay: {item.vegan}",
        f"Dị ứng: {allergens_str}",
        f"Thành phần: {item.ingredients}",
        f"Mô tả: {item.description_vi}",
    ]
    return " | ".join(p for p in parts if p)


def parse_menu_row(row: dict[str, str]) -> MenuItemRecord:
    """Convert a raw CSV row into a validated MenuItemRecord."""
    def parse_price(val: str | None) -> int | None:
        if not val or not val.strip() or val.strip().lower() in ("0", "none", "null"):
            return None
        try:
            return int(float(val.strip()))
        except ValueError:
            return None

    sizes = [s.strip() for s in row.get("sizes", "").split("/") if s.strip()]
    allergens_raw = row.get("allergens", "")
    allergens = [
        a.strip()
        for a in allergens_raw.split(",")
        if a.strip() and a.strip().lower() not in ("không", "none", "null")
    ]

    return MenuItemRecord(
        item_id=row["item_id"].strip(),
        name_vi=row["name_vi"].strip(),
        name_en=row.get("name_en", "").strip(),
        category=row["category"].strip(),
        category_en=row.get("category_en", "").strip(),
        price_s=parse_price(row.get("price_s")),
        price_m=parse_price(row.get("price_m")),
        price_l=parse_price(row.get("price_l")),
        sizes=sizes,
        temperature=row.get("temperature", "any").strip(),
        caffeine=row.get("caffeine", "không").strip(),
        vegan=row.get("vegan", "không").strip(),
        allergens=allergens,
        ingredients=row.get("ingredients", "").strip(),
        description_vi=row.get("description_vi", "").strip(),
        description_en=row.get("description_en", "").strip(),
    )


class MenuIngestor(BaseIngestor):
    def __init__(
        self,
        csv_path: Path,
        repository: Neo4jRepository,
        embeddings_client: EmbeddingsClient,
        batch_size: int = 20,
    ):
        self.csv_path = Path(csv_path)
        self.repository = repository
        self.embeddings = embeddings_client
        self.batch_size = batch_size

    async def ingest(self) -> int:
        if not self.csv_path.is_file():
            raise FileNotFoundError(f"Menu CSV not found at {self.csv_path}")

        logger.info("STAGE MenuIngestor.ingest START from %s", self.csv_path)
        items: list[MenuItemRecord] = []
        with self.csv_path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item_id = row.get("item_id")
                if item_id:
                    items.append(parse_menu_row(row))

        total_items = len(items)
        logger.info("Parsed %d items from menu CSV. Ingesting in batches of %d...", total_items, self.batch_size)

        ingested_count = 0
        for i in range(0, total_items, self.batch_size):
            batch = items[i : i + self.batch_size]
            texts = [build_menu_item_embedding_text(it) for it in batch]
            vectors = await self.embeddings.get_embeddings_batch(texts)

            for item, vector in zip(batch, vectors, strict=True):
                await self.repository.upsert_menu_item(item, vector)
                ingested_count += 1

            logger.info("Ingested %d/%d items...", ingested_count, total_items)

        logger.info("STAGE MenuIngestor.ingest COMPLETE: %s", dump_json({"total_ingested": ingested_count}))
        return ingested_count
