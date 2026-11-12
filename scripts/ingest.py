"""CLI script for ingesting knowledge base data into Neo4j Aura.

Usage:
    uv run python scripts/ingest.py --target menu
"""

import argparse
import asyncio
import logging
from pathlib import Path

from src.config import get_settings
from src.observability.logging import job_context, setup_logging
from src.rag.embeddings import EmbeddingsClient
from src.rag.graph.client import Neo4jClient
from src.rag.graph.repository import Neo4jRepository
from src.rag.ingestion.menu import MenuIngestor

logger = logging.getLogger(__name__)


async def run_ingestion(target: str) -> None:
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

    try:
        # Step 1: Ensure Schema & Vector index exist
        logger.info("Connecting to Neo4j Aura and ensuring constraints & vector index...")
        await repository.init_schema(vector_dimensions=settings.vector_dimensions)

        # Step 2: Ingest based on target
        if target in ("menu", "all"):
            menu_csv = Path(__file__).resolve().parents[1] / "data" / "raw" / "menu" / "menu.csv"
            ingestor = MenuIngestor(
                csv_path=menu_csv,
                repository=repository,
                embeddings_client=embeddings_client,
                batch_size=25,
            )
            count = await ingestor.ingest()
            print(f"[OK] Successfully ingested {count} menu items into Neo4j Aura.")
        else:
            print(f"[WARN] Unknown target: {target}")

    finally:
        await embeddings_client.aclose()
        await neo4j_client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Knowledge Base data into Neo4j Aura.")
    parser.add_argument(
        "--target",
        choices=["menu", "faq", "docs", "all"],
        default="menu",
        help="Target data to ingest (default: menu)",
    )
    args = parser.parse_args()

    setup_logging(console=True)
    with job_context("ingest_" + args.target):
        asyncio.run(run_ingestion(args.target))


if __name__ == "__main__":
    main()

