"""Benchmark Hybrid Graph RAG retrieval on `data/evaluation/rag_eval_20.json` against Neo4j Aura."""

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.rag.embeddings import EmbeddingsClient
from src.rag.graph.client import Neo4jClient
from src.rag.graph.repository import Neo4jRepository
from src.rag.retrieval.hybrid_search import HybridRetriever


def _evaluate_hit(case: dict[str, Any], retrieved_ids: set[str]) -> tuple[bool, dict[str, Any]]:
    gold_menus = set(case.get("gold_menu_ids", []))
    gold_faqs = {f"faq-{fid}" for fid in case.get("gold_faq_ids", [])}
    gold_docs = {f"doc-{sec}" for sec in case.get("gold_doc_sections", [])}

    if not case.get("answerable", True):
        # For unanswerable questions, none of the gold sets exist
        return True, {"matched": []}

    matched_menus = sorted(gold_menus & retrieved_ids)
    matched_faqs = sorted(gold_faqs & retrieved_ids)
    matched_docs = sorted(gold_docs & retrieved_ids)
    all_matched = matched_menus + matched_faqs + matched_docs

    if case.get("needs_graph_expansion"):
        # Multi-chunk questions require ALL gold_doc_sections to be retrieved
        hit = gold_docs.issubset(retrieved_ids)
    else:
        hit = bool(all_matched)

    return hit, {
        "matched_menus": matched_menus,
        "matched_faqs": matched_faqs,
        "matched_docs": matched_docs,
    }


async def run_benchmark(top_k: int = 8) -> dict[str, Any]:
    settings = get_settings()
    base_dir = Path(__file__).resolve().parents[2]
    eval_path = base_dir / "data" / "evaluation" / "rag_eval_20.json"
    cases = json.loads(eval_path.read_text(encoding="utf-8"))

    neo4j_client = Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password.get_secret_value(),
        database=settings.neo4j_database,
    )
    repository = Neo4jRepository(neo4j_client)

    model_name = settings.embedding_model
    if "/" not in model_name:
        model_name = f"google/{model_name}"

    embeddings_client = EmbeddingsClient(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
        model=model_name,
        dimensions=settings.vector_dimensions,
    )

    retriever = HybridRetriever(
        repository=repository,
        embeddings_client=embeddings_client,
        min_score=0.60,
        evidence_threshold=0.70,
    )

    results: list[dict[str, Any]] = []
    answerable_hits = 0
    answerable_total = 0
    multi_chunk_hits = 0
    multi_chunk_total = 0

    try:
        for case in cases:
            t0 = time.perf_counter()
            res = await retriever.retrieve(case["question"], top_k=top_k)
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

            retrieved_ids = {item.node_id for item in res.items}
            hit, details = _evaluate_hit(case, retrieved_ids)

            if case.get("answerable", True):
                answerable_total += 1
                if hit:
                    answerable_hits += 1
            if case.get("needs_graph_expansion"):
                multi_chunk_total += 1
                if hit:
                    multi_chunk_hits += 1

            row = {
                "id": case["id"],
                "type": case["type"],
                "question": case["question"],
                "hit": hit,
                "elapsed_ms": elapsed_ms,
                "retrieved_ids": [item.node_id for item in res.items],
                "hop_types": [item.hop_type for item in res.items],
                "details": details,
            }
            results.append(row)
            status = "PASS" if hit else "MISS"
            print(
                f"[{status}] {case['id']} ({case['type']}) - {elapsed_ms}ms - top={row['retrieved_ids'][:4]}"
            )
    finally:
        await embeddings_client.aclose()
        await neo4j_client.close()

    summary = {
        "answerable_recall": f"{answerable_hits}/{answerable_total} ({round(answerable_hits / max(1, answerable_total) * 100, 1)}%)",
        "multi_chunk_graph_recall": f"{multi_chunk_hits}/{multi_chunk_total} ({round(multi_chunk_hits / max(1, multi_chunk_total) * 100, 1)}%)",
        "results": results,
    }
    print("\n=== BENCHMARK SUMMARY ===")
    print(f"Answerable Recall@{top_k}: {summary['answerable_recall']}")
    print(f"Multi-Chunk Graph Expansion Recall: {summary['multi_chunk_graph_recall']}")
    return summary


if __name__ == "__main__":
    asyncio.run(run_benchmark())
