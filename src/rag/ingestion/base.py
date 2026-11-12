"""Base contract for RAG data ingestion."""

from abc import ABC, abstractmethod


class BaseIngestor(ABC):
    @abstractmethod
    async def ingest(self) -> int:
        """Run the ingestion pipeline and return the count of ingested items."""

