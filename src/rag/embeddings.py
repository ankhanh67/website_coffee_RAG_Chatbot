"""Embeddings client using OpenRouter / OpenAI embeddings API."""

import logging

from openai import AsyncOpenAI

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
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def get_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for a single string."""
        vectors = await self.get_embeddings_batch([text])
        return vectors[0]

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of strings."""
        if not texts:
            return []

        logger.info(
            "STAGE EmbeddingsClient.get_embeddings_batch INPUT: %s",
            dump_json({"count": len(texts), "model": self.model, "dimensions": self.dimensions}),
        )
        try:
            kwargs = {"model": self.model, "input": texts}
            if self.dimensions:
                kwargs["dimensions"] = self.dimensions

            response = await self._client.embeddings.create(**kwargs)
            vectors = [item.embedding for item in response.data]
            logger.info(
                "STAGE EmbeddingsClient.get_embeddings_batch OUTPUT: %s",
                dump_json({"count": len(vectors), "dimensions": len(vectors[0]) if vectors else 0}),
            )
            return vectors
        except Exception as e:
            logger.error("Failed to generate embeddings: %s", e)
            raise ModelServiceUnavailableError(f"Embedding generation failed: {e}") from e

    async def aclose(self) -> None:
        await self._client.close()
