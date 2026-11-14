"""Embeddings client using LangChain OpenAIEmbeddings via OpenRouter."""

import logging

from langchain_openai import OpenAIEmbeddings
from openai import OpenAIError
from pydantic import SecretStr

from src.exceptions import ModelServiceUnavailableError
from src.observability.logging import dump_json

logger = logging.getLogger(__name__)


class EmbeddingsClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "google/gemini-embedding-001",
        dimensions: int = 768,
    ):
        self.model = model
        self.dimensions = dimensions
        self._embeddings = OpenAIEmbeddings(
            model=model,
            api_key=SecretStr(api_key),
            base_url=base_url,
            dimensions=dimensions if dimensions else None,
            check_embedding_ctx_length=False,
        )

    @property
    def langchain_embeddings(self) -> OpenAIEmbeddings:
        """Expose the underlying LangChain OpenAIEmbeddings instance."""
        return self._embeddings

    async def get_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for a single string via LangChain OpenAIEmbeddings."""
        vectors = await self.get_embeddings_batch([text])
        return vectors[0]

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of strings via LangChain OpenAIEmbeddings."""
        if not texts:
            return []

        logger.info(
            "STAGE EmbeddingsClient.get_embeddings_batch INPUT: %s",
            dump_json({"count": len(texts), "model": self.model, "dimensions": self.dimensions}),
        )
        try:
            vectors = await self._embeddings.aembed_documents(texts)
            logger.info(
                "STAGE EmbeddingsClient.get_embeddings_batch OUTPUT: %s",
                dump_json({"count": len(vectors), "dimensions": len(vectors[0]) if vectors else 0}),
            )
            return vectors
        except (OpenAIError, ValueError, TypeError, RuntimeError) as e:
            logger.error("Failed to generate embeddings: %s", e)
            raise ModelServiceUnavailableError(f"Embedding generation failed: {e}") from e

    async def aclose(self) -> None:
        async_client = getattr(self._embeddings, "async_client", None)
        root_client = getattr(async_client, "_client", None)
        if root_client is not None and hasattr(root_client, "close"):
            res = root_client.close()
            if hasattr(res, "__await__"):
                await res
