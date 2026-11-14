"""End-to-end RAG evaluation on `data/evaluation/rag_eval_20.json` through ConsultantAgent and FAQAgent."""

import asyncio
import json
import time
import unicodedata
from pathlib import Path
from typing import Any

from src.config import get_settings
from src.infrastructure.model_client import ModelClient
from src.rag.embeddings import EmbeddingsClient
from src.rag.graph.client import Neo4jClient
from src.rag.graph.repository import Neo4jRepository
from src.rag.retrieval.hybrid_search import HybridRetriever
from src.subagents.consultant_agent import ConsultantAgent
from src.subagents.faq_agent import FAQAgent


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower()


def _check_keywords(reply: str, case: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    norm_reply = _normalize(reply)
    # Also create a version without thousand-separator dots/commas so '65.000' matches '65,000' or '65000'
    compact_reply = norm_reply.replace(".", "").replace(",", "")

    matched_kw: list[str] = []
    missing_kw: list[str] = []
    for kw in case.get("answer_keywords", []):
        norm_kw = _normalize(kw)
        compact_kw = norm_kw.replace(".", "").replace(",", "")
        if norm_kw in norm_reply or (compact_kw and compact_kw in compact_reply):
            matched_kw.append(kw)
        else:
            missing_kw.append(kw)

    forbidden_hit: list[str] = []
    for fkw in case.get("forbidden_keywords", []):
        if _normalize(fkw) in norm_reply:
            forbidden_hit.append(fkw)

    passed = (len(missing_kw) == 0) and (len(forbidden_hit) == 0)
    return passed, matched_kw, missing_kw


async def run_e2e_evaluation(limit: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    base_dir = Path(__file__).resolve().parents[2]
    eval_path = base_dir / "data" / "evaluation" / "rag_eval_20.json"
    cases = json.loads(eval_path.read_text(encoding="utf-8"))
    if limit is not None:
        cases = cases[:limit]

    neo4j_client = Neo4jClient(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password.get_secret_value(),
        database=settings.neo4j_database,
    )
    repository = Neo4jRepository(neo4j_client)

    emb_model = settings.embedding_model
    if "/" not in emb_model:
        emb_model = f"google/{emb_model}"

    embeddings_client = EmbeddingsClient(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
        model=emb_model,
        dimensions=settings.vector_dimensions,
    )
    model_client = ModelClient(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
    )
    retriever = HybridRetriever(
        repository=repository,
        embeddings_client=embeddings_client,
        min_score=0.60,
        evidence_threshold=0.70,
    )

    consultant_agent = ConsultantAgent(
        model_client=model_client,
        retriever=retriever,
        model=settings.llm_generator_model,
    )
    faq_agent = FAQAgent(
        model_client=model_client,
        retriever=retriever,
        model=settings.llm_generator_model,
    )

    passed_count = 0
    rows: list[dict[str, Any]] = []

    try:
        for case in cases:
            q_type = case.get("type", "faq")
            agent = consultant_agent if q_type == "menu" else faq_agent
            t0 = time.perf_counter()
            reply = await agent.handle(
                message=case["question"],
                session_id=f"eval-{case['id']}",
            )
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

            passed, matched_kw, missing_kw = _check_keywords(reply, case)
            if passed:
                passed_count += 1

            status = "PASS" if passed else "MISS"
            print(
                f"[{status}] {case['id']} ({q_type}) - {elapsed_ms}ms - missing={missing_kw}"
            )
            rows.append({
                "id": case["id"],
                "type": q_type,
                "question": case["question"],
                "passed": passed,
                "matched_keywords": matched_kw,
                "missing_keywords": missing_kw,
                "elapsed_ms": elapsed_ms,
                "reply": reply,
            })
    finally:
        await model_client.aclose()
        await embeddings_client.aclose()
        await neo4j_client.close()

    total = len(cases)
    accuracy_str = f"{passed_count}/{total} ({round(passed_count / max(1, total) * 100, 1)}%)"
    print(f"\n=== E2E GENERATION SUMMARY ===\nKeyword & Refusal Accuracy: {accuracy_str}")
    return {"accuracy": accuracy_str, "results": rows}


if __name__ == "__main__":
    asyncio.run(run_e2e_evaluation())
