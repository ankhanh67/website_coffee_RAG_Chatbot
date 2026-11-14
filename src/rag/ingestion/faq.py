"""Ingest FAQ Q&A pairs from data/raw/faq/faq.csv into Neo4j Aura as Chunk nodes."""

import csv
import logging
from pathlib import Path
from typing import Protocol

from src.observability.logging import dump_json
from src.rag.ingestion.base import BaseIngestor
from src.schema.retrieval import ChunkRecord

logger = logging.getLogger(__name__)


class ChunkRepository(Protocol):
    async def upsert_chunk(self, chunk: ChunkRecord, embedding: list[float]) -> str: ...


class BatchEmbeddingsProvider(Protocol):
    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]: ...


def parse_faq_row(row: dict[str, str]) -> ChunkRecord:
    faq_id = row["faq_id"].strip()
    question = row.get("question", "").strip()
    answer = row.get("answer", "").strip()
    topic_id = row.get("topic_id", "").strip()
    category = row.get("category", "").strip()
    language = row.get("language", "vi").strip()

    text = f"Hỏi: {question}\nĐáp: {answer}"

    return ChunkRecord(
        chunk_id=f"faq-{faq_id}",
        source="faq",
        title=question,
        text=text,
        doc_id="faq",
        order=0,
        file="faq.csv",
        metadata={
            "topic_id": topic_id,
            "category": category,
            "language": language,
        },
    )


class FAQIngestor(BaseIngestor):
    def __init__(
        self,
        csv_path: Path,
        repository: ChunkRepository,
        embeddings_client: BatchEmbeddingsProvider,
        batch_size: int = 25,
    ) -> None:
        self.csv_path = Path(csv_path)
        self.repository = repository
        self.embeddings = embeddings_client
        self.batch_size = batch_size

    async def ingest(self) -> int:
        if not self.csv_path.is_file():
            raise FileNotFoundError(f"FAQ CSV not found at {self.csv_path}")

        logger.info("STAGE FAQIngestor.ingest START from %s", self.csv_path)
        chunks: list[ChunkRecord] = []
        with self.csv_path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("faq_id"):
                    chunks.append(parse_faq_row(row))

        total_chunks = len(chunks)
        logger.info("Parsed %d FAQ chunks. Ingesting in batches of %d...", total_chunks, self.batch_size)

        ingested_count = 0
        for i in range(0, total_chunks, self.batch_size):
            batch = chunks[i : i + self.batch_size]
            texts = [c.text for c in batch]
            vectors = await self.embeddings.get_embeddings_batch(texts)

            for chunk, vector in zip(batch, vectors, strict=True):
                await self.repository.upsert_chunk(chunk, vector)
                ingested_count += 1

            logger.info("Ingested %d/%d FAQ chunks...", ingested_count, total_chunks)

        logger.info("STAGE FAQIngestor.ingest COMPLETE: %s", dump_json({"total_ingested": ingested_count}))
        return ingested_count

