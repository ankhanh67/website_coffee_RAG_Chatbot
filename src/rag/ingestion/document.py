"""Document ingestor: loads sections, generates embeddings, links [:NEXT] and [:MENTIONS]."""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Protocol

from src.observability.logging import dump_json
from src.rag.ingestion.base import BaseIngestor
from src.rag.ingestion.chunker import DocumentChunker
from src.schema.retrieval import ChunkRecord, EntityRecord

logger = logging.getLogger(__name__)


class DocumentRepository(Protocol):
    async def upsert_chunk(self, chunk: ChunkRecord, embedding: list[float]) -> str: ...
    async def link_chunks_next(self, c1_id: str, c2_id: str) -> None: ...
    async def link_chunk_mentions(self, chunk_id: str, entity: EntityRecord) -> None: ...


class DocumentEmbeddingsProvider(Protocol):
    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]: ...


class EntityExtractionProvider(Protocol):
    async def extract_entities(self, text: str) -> list[EntityRecord]: ...


class DocumentIngestor(BaseIngestor):
    def __init__(
        self,
        manifest_path: Path,
        repository: DocumentRepository,
        embeddings_client: DocumentEmbeddingsProvider,
        entity_extractor: EntityExtractionProvider,
        batch_size: int = 20,
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.repository = repository
        self.embeddings = embeddings_client
        self.extractor = entity_extractor
        self.batch_size = batch_size

    async def ingest(self) -> int:
        if not self.manifest_path.is_file():
            raise FileNotFoundError(f"Manifest not found at {self.manifest_path}")

        logger.info("STAGE DocumentIngestor.ingest START from %s", self.manifest_path)
        chunks = DocumentChunker.load_manifest(self.manifest_path)
        total_chunks = len(chunks)
        logger.info("Loaded %d document chunks. Ingesting in batches of %d...", total_chunks, self.batch_size)

        ingested_count = 0
        for i in range(0, total_chunks, self.batch_size):
            batch = chunks[i : i + self.batch_size]
            texts = [c.text for c in batch]
            vectors = await self.embeddings.get_embeddings_batch(texts)

            for chunk, vector in zip(batch, vectors, strict=True):
                await self.repository.upsert_chunk(chunk, vector)
                entities = await self.extractor.extract_entities(chunk.text)
                for entity in entities:
                    await self.repository.link_chunk_mentions(chunk.chunk_id, entity)
                ingested_count += 1

            logger.info("Ingested %d/%d document chunks...", ingested_count, total_chunks)

        # Link [:NEXT] relationships for adjacent chunks within each doc_id
        doc_groups: dict[str, list[ChunkRecord]] = defaultdict(list)
        for chunk in chunks:
            doc_groups[chunk.doc_id].append(chunk)

        linked_next_count = 0
        for doc_chunks in doc_groups.values():
            sorted_chunks = sorted(doc_chunks, key=lambda c: c.order)
            for j in range(len(sorted_chunks) - 1):
                c1, c2 = sorted_chunks[j], sorted_chunks[j + 1]
                if c2.order == c1.order + 1:
                    await self.repository.link_chunks_next(c1.chunk_id, c2.chunk_id)
                    linked_next_count += 1

        logger.info(
            "STAGE DocumentIngestor.ingest COMPLETE: %s",
            dump_json({"total_ingested": ingested_count, "linked_next": linked_next_count}),
        )
        return ingested_count
