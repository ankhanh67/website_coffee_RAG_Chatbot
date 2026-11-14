"""Unified HybridRetriever orchestrating Vector Search + Graph Traversal + Reranker."""

import logging
from typing import Protocol

from src.observability.logging import dump_json
from src.rag.retrieval.base import BaseRetriever
from src.rag.retrieval.graph_search import GraphSearcher, GraphSearchRepository
from src.rag.retrieval.reranker import HybridReranker
from src.rag.retrieval.vector_search import VectorSearcher, VectorSearchRepository
from src.schema.retrieval import HybridRetrievalResult

logger = logging.getLogger(__name__)


class QueryEmbeddingProvider(Protocol):
    async def get_embedding(self, text: str) -> list[float]: ...


class HybridRepositoryProtocol(VectorSearchRepository, GraphSearchRepository, Protocol):
    """Combined repository protocol supporting both vector search and graph expansion."""


class HybridRetriever(BaseRetriever):
    def __init__(
        self,
        repository: HybridRepositoryProtocol,
        embeddings_client: QueryEmbeddingProvider,
        vector_searcher: VectorSearcher | None = None,
        graph_searcher: GraphSearcher | None = None,
        reranker: HybridReranker | None = None,
        min_score: float = 0.65,
        evidence_threshold: float = 0.72,
    ) -> None:
        self._repository = repository
        self._embeddings = embeddings_client
        self._min_score = min_score
        self._evidence_threshold = evidence_threshold
        self._vector_searcher = vector_searcher or VectorSearcher(repository)
        self._graph_searcher = graph_searcher or GraphSearcher(repository)
        self._reranker = reranker or HybridReranker(min_score=min_score)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        include_menu: bool = True,
        include_chunks: bool = True,
        expand_graph: bool = True,
    ) -> HybridRetrievalResult:
        cleaned_query = query.strip()
        if not cleaned_query:
            return HybridRetrievalResult(query=query, items=[], has_sufficient_evidence=False)

        logger.info(
            "STAGE HybridRetriever.retrieve INPUT: %s",
            dump_json(
                {
                    "query": cleaned_query,
                    "top_k": top_k,
                    "include_menu": include_menu,
                    "include_chunks": include_chunks,
                    "expand_graph": expand_graph,
                }
            ),
        )
        embedding = await self._embeddings.get_embedding(cleaned_query)

        candidate_k = max(top_k * 2, 12)
        vector_items = await self._vector_searcher.search_all(
            embedding=embedding,
            top_k=candidate_k,
            min_score=self._min_score,
            include_menu=include_menu,
            include_chunks=include_chunks,
        )

        # Sort initial vector items by score descending before picking graph expansion seeds
        vector_items.sort(key=lambda x: x.score, reverse=True)

        graph_items = []
        if expand_graph and include_chunks and vector_items:
            graph_items = await self._graph_searcher.expand(vector_items)

        ranked_items = self._reranker.rerank(
            query=cleaned_query,
            vector_items=vector_items,
            graph_items=graph_items,
            top_k=top_k,
        )

        has_evidence = bool(
            ranked_items and ranked_items[0].score >= self._evidence_threshold
        )

        result = HybridRetrievalResult(
            query=cleaned_query,
            items=ranked_items,
            has_sufficient_evidence=has_evidence,
        )
        logger.info(
            "STAGE HybridRetriever.retrieve OUTPUT: %s",
            dump_json(
                {
                    "count": len(ranked_items),
                    "has_sufficient_evidence": has_evidence,
                    "top_ids": [item.node_id for item in ranked_items],
                }
            ),
        )
        return result
