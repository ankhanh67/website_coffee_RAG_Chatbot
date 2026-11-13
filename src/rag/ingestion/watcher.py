"""Watchdog observer for data/inbox/ to ingest newly dropped docx, pdf, and csv files."""

import asyncio
import logging
from pathlib import Path
from typing import Protocol

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from src.observability.logging import dump_json
from src.rag.ingestion.chunker import DocumentChunker
from src.rag.ingestion.faq import FAQIngestor
from src.rag.ingestion.menu import MenuIngestor
from src.schema.retrieval import ChunkRecord, EntityRecord, MenuItemRecord

logger = logging.getLogger(__name__)


class WatcherRepository(Protocol):
    async def upsert_chunk(self, chunk: ChunkRecord, embedding: list[float]) -> str: ...
    async def link_chunk_mentions(self, chunk_id: str, entity: EntityRecord) -> None: ...
    async def upsert_menu_item(self, item: MenuItemRecord, embedding: list[float]) -> str: ...


class WatcherEmbeddingsClient(Protocol):
    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]: ...


class WatcherEntityExtractor(Protocol):
    async def extract_entities(self, text: str) -> list[EntityRecord]: ...


class InboxHandler(FileSystemEventHandler):
    def __init__(self, watcher: "InboxWatcher") -> None:
        self.watcher = watcher

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        logger.info("InboxHandler detected new file: %s", path)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.watcher.process_file(path))
        except RuntimeError:
            asyncio.run(self.watcher.process_file(path))


class InboxWatcher:
    def __init__(
        self,
        inbox_dir: Path,
        repository: WatcherRepository,
        embeddings_client: WatcherEmbeddingsClient,
        entity_extractor: WatcherEntityExtractor,
    ) -> None:
        self.inbox_dir = Path(inbox_dir)
        self.repository = repository
        self.embeddings = embeddings_client
        self.extractor = entity_extractor
        self._observer: Observer | None = None

    async def process_file(self, file_path: Path) -> int:
        path = Path(file_path)
        if not path.is_file():
            return 0

        suffix = path.suffix.lower()
        logger.info("STAGE InboxWatcher.process_file START: %s (%s)", path.name, suffix)

        if suffix == ".csv":
            # Check if FAQ or Menu by inspecting header
            with path.open(encoding="utf-8-sig") as f:  # noqa: ASYNC230
                header = f.readline()
            if "faq_id" in header:
                ingestor = FAQIngestor(
                    csv_path=path,
                    repository=self.repository,  # type: ignore[arg-type]
                    embeddings_client=self.embeddings,
                )
                return await ingestor.ingest()
            if "item_id" in header:
                ingestor_menu = MenuIngestor(
                    csv_path=path,
                    repository=self.repository,  # type: ignore[arg-type]
                    embeddings_client=self.embeddings,  # type: ignore[arg-type]
                )
                return await ingestor_menu.ingest()
            return 0

        chunks: list[ChunkRecord] = []
        doc_id = path.stem.lower()

        if suffix == ".docx":
            chunks = DocumentChunker.parse_docx(path, doc_id=doc_id)
        elif suffix == ".pdf":
            chunks = DocumentChunker.parse_pdf(path, doc_id=doc_id)
        else:
            logger.info("Unsupported file type in inbox: %s", suffix)
            return 0

        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        vectors = await self.embeddings.get_embeddings_batch(texts)
        count = 0
        for chunk, vector in zip(chunks, vectors, strict=True):
            await self.repository.upsert_chunk(chunk, vector)
            entities = await self.extractor.extract_entities(chunk.text)
            for entity in entities:
                await self.repository.link_chunk_mentions(chunk.chunk_id, entity)
            count += 1

        logger.info("STAGE InboxWatcher.process_file COMPLETE: %s", dump_json({"count": count}))
        return count

    def start(self) -> None:
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self._observer = Observer()
        handler = InboxHandler(self)
        self._observer.schedule(handler, str(self.inbox_dir), recursive=False)
        self._observer.start()
        logger.info("InboxWatcher started monitoring %s", self.inbox_dir)

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            logger.info("InboxWatcher stopped.")
