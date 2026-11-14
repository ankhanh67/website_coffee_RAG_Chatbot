"""CLI script for ingesting knowledge base data into Neo4j Aura.

Usage:
    uv run python scripts/ingest.py --target menu
    uv run python scripts/ingest.py --target faq
    uv run python scripts/ingest.py --target docs
    uv run python scripts/ingest.py --target all
    uv run python scripts/ingest.py --watch
"""

import argparse
import asyncio
import logging
from pathlib import Path

from src.config import get_settings
from src.infrastructure.model_client import ModelClient
from src.observability.logging import job_context, setup_logging
from src.rag.embeddings import EmbeddingsClient
from src.rag.graph.client import Neo4jClient
from src.rag.graph.repository import Neo4jRepository
from src.rag.ingestion.document import DocumentIngestor
from src.rag.ingestion.entity_extractor import EntityExtractor
from src.rag.ingestion.faq import FAQIngestor
from src.rag.ingestion.menu import MenuIngestor
from src.rag.ingestion.watcher import InboxWatcher

logger = logging.getLogger(__name__)


async def run_ingestion(target: str, watch: bool = False) -> None:
    settings = get_settings()

    neo4j_client = Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password.get_secret_value(),
        database=settings.neo4j_database,
    )
    repository = Neo4jRepository(neo4j_client)

    embeddings_client = EmbeddingsClient(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
        model=settings.embedding_model,
        dimensions=settings.vector_dimensions,
    )

    model_client = ModelClient(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
    )
    entity_extractor = EntityExtractor(
        model_client=model_client,
        model=settings.generation_model,
    )
    base_dir = Path(__file__).resolve().parents[1]

    try:
        # Step 1: Ensure Schemas & Vector indexes exist
        logger.info("Connecting to Neo4j Aura and ensuring constraints & vector indexes...")
        await repository.init_schema(vector_dimensions=settings.vector_dimensions)
        await repository.init_chunk_schema(vector_dimensions=settings.vector_dimensions)

        # Step 2: Ingest based on target
        if target in ("menu", "all"):
            menu_csv = base_dir / "data" / "raw" / "menu" / "menu.csv"
            ingestor_menu = MenuIngestor(
                csv_path=menu_csv,
                repository=repository,
                embeddings_client=embeddings_client,
                batch_size=25,
            )
            count = await ingestor_menu.ingest()
            print(f"[OK] Successfully ingested {count} menu items into Neo4j Aura.")

        if target in ("faq", "all"):
            faq_csv = base_dir / "data" / "raw" / "faq" / "faq.csv"
            ingestor_faq = FAQIngestor(
                csv_path=faq_csv,
                repository=repository,
                embeddings_client=embeddings_client,
                batch_size=25,
            )
            count_faq = await ingestor_faq.ingest()
            print(f"[OK] Successfully ingested {count_faq} FAQ Q&A chunks into Neo4j Aura.")

        if target in ("docs", "all"):
            manifest_json = base_dir / "data" / "raw" / "documents" / "doc_sections_manifest.json"
            ingestor_docs = DocumentIngestor(
                manifest_path=manifest_json,
                repository=repository,
                embeddings_client=embeddings_client,
                entity_extractor=entity_extractor,
                batch_size=20,
            )
            count_docs = await ingestor_docs.ingest()
            print(f"[OK] Successfully ingested {count_docs} document chunks with graph links into Neo4j Aura.")

        # Step 3: Watch mode
        if watch:
            inbox_dir = base_dir / "data" / "inbox"
            inbox_dir.mkdir(parents=True, exist_ok=True)
            watcher = InboxWatcher(
                inbox_dir=inbox_dir,
                repository=repository,
                embeddings_client=embeddings_client,
                entity_extractor=entity_extractor,
            )
            watcher.start()
            print(f"[WATCH] Watching {inbox_dir} for new files. Press Ctrl+C to stop.")
            try:
                while True:
                    await asyncio.sleep(1)
            except (KeyboardInterrupt, asyncio.CancelledError):
                watcher.stop()
                print("[WATCH] Stopped.")

    finally:
        await model_client.aclose()
        await embeddings_client.aclose()
        await neo4j_client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Knowledge Base data into Neo4j Aura.")
    parser.add_argument(
        "--target",
        choices=["menu", "faq", "docs", "all"],
        default="all",
        help="Target data to ingest (default: all)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Keep running and watch data/inbox/ for new files",
    )
    args = parser.parse_args()

    setup_logging(console=True)
    with job_context("ingest_" + args.target):
        asyncio.run(run_ingestion(args.target, watch=args.watch))


if __name__ == "__main__":
    main()
