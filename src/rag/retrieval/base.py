"""Base contract for retrieval components."""

from abc import ABC, abstractmethod

from src.schema.retrieval import HybridRetrievalResult


class BaseRetriever(ABC):
    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 5) -> HybridRetrievalResult:
        """Retrieve relevant documents/menu items for a user query."""
