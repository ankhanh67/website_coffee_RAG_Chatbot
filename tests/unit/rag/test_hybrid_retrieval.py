"""Unit tests for Phase 6 Hybrid Graph RAG: VectorSearcher, GraphSearcher, HybridReranker, HybridRetriever."""

from unittest.mock import AsyncMock

from src.rag.retrieval.graph_search import GraphSearcher
from src.rag.retrieval.hybrid_search import HybridRetriever
from src.rag.retrieval.reranker import HybridReranker
from src.rag.retrieval.vector_search import VectorSearcher
from src.schema.retrieval import ChunkRecord, MenuItemRecord


def make_sample_chunks() -> tuple[ChunkRecord, ChunkRecord, ChunkRecord]:
    c1 = ChunkRecord(
        chunk_id="doc-policy-08",
        source="document",
        title="Hạng Vàng",
        text="Hạng Vàng cần tích lũy từ 500 điểm thưởng trong năm.",
        doc_id="policy",
        order=8,
        file="policy.docx",
    )
    c2 = ChunkRecord(
        chunk_id="doc-policy-09",
        source="document",
        title="Đổi điểm thưởng",
        text="100 điểm thưởng đổi được 1 đồ uống size M bất kỳ. Điểm có hạn 12 tháng.",
        doc_id="policy",
        order=9,
        file="policy.docx",
    )
    c3 = ChunkRecord(
        chunk_id="faq-F141",
        source="faq",
        title="Chi nhánh yên tĩnh ở Hà Nội",
        text="Hỏi: Chi nhánh nào ở Hà Nội có khu làm việc yên tĩnh?\nĐáp: Chi nhánh Cầu Giấy có khu làm việc yên tĩnh.",
        doc_id="faq",
        order=0,
        file="faq.csv",
    )
    return c1, c2, c3


def make_sample_menu() -> MenuItemRecord:
    return MenuItemRecord(
        item_id="M002",
        name_vi="Phin Đen Đá",
        name_en="Iced Black Coffee",
        category="Cà phê",
        category_en="Coffee",
        price_s=29000,
        price_m=35000,
        price_l=45000,
        sizes=["S", "M", "L"],
        temperature="iced",
        caffeine="có",
        vegan="có",
        allergens=[],
    )


async def test_vector_searcher_searches_chunks_and_menu():
    c1, _, _ = make_sample_chunks()
    m1 = make_sample_menu()

    repo = AsyncMock()
    repo.search_chunks_by_vector.return_value = [(c1, 0.88)]
    repo.search_menu_items_by_vector.return_value = [(m1, 0.91)]

    searcher = VectorSearcher(repo)
    items = await searcher.search_all(embedding=[0.1] * 768, top_k=5, min_score=0.65)

    assert len(items) == 2
    node_ids = {item.node_id for item in items}
    assert "doc-policy-08" in node_ids
    assert "M002" in node_ids
    menu_item = next(i for i in items if i.node_id == "M002")
    assert "35.000đ" in menu_item.text


async def test_graph_searcher_expands_next_and_entities():
    c1, c2, c3 = make_sample_chunks()

    repo = AsyncMock()
    repo.expand_chunks_next.return_value = [(c2, "doc-policy-08")]
    repo.expand_chunks_by_entities.return_value = [(c3, "doc-policy-08", "branch_cau_giay")]

    vector_searcher = VectorSearcher(repo)
    repo.search_chunks_by_vector.return_value = [(c1, 0.90)]
    seeds = await vector_searcher.search_chunks([0.1] * 768)

    graph_searcher = GraphSearcher(repo, next_decay=0.92, entity_decay=0.88)
    expanded = await graph_searcher.expand(seeds)

    assert len(expanded) == 2
    next_item = next(i for i in expanded if i.node_id == "doc-policy-09")
    entity_item = next(i for i in expanded if i.node_id == "faq-F141")
    assert next_item.hop_type == "next"
    assert next_item.score == round(0.90 * 0.92, 4)
    assert entity_item.hop_type == "entity"
    assert entity_item.metadata["shared_entity"] == "branch_cau_giay"


async def test_hybrid_retriever_combines_vector_and_graph_and_checks_evidence():
    c1, c2, _ = make_sample_chunks()

    repo = AsyncMock()
    repo.search_chunks_by_vector.return_value = [(c1, 0.89)]
    repo.search_menu_items_by_vector.return_value = []
    repo.expand_chunks_next.return_value = [(c2, "doc-policy-08")]
    repo.expand_chunks_by_entities.return_value = []

    embeddings = AsyncMock()
    embeddings.get_embedding.return_value = [0.1] * 768

    retriever = HybridRetriever(
        repository=repo,
        embeddings_client=embeddings,
        min_score=0.65,
        evidence_threshold=0.72,
    )
    res = await retriever.retrieve(
        "Hạng Vàng cần bao nhiêu điểm và điểm thưởng đổi được gì?",
        top_k=5,
    )

    assert res.has_sufficient_evidence is True
    retrieved_ids = [item.node_id for item in res.items]
    # Both policy-08 (from vector) and policy-09 (from [:NEXT] graph expansion) must be retrieved!
    assert "doc-policy-08" in retrieved_ids
    assert "doc-policy-09" in retrieved_ids


async def test_hybrid_retriever_marks_insufficient_evidence_when_below_threshold():
    repo = AsyncMock()
    repo.search_chunks_by_vector.return_value = []
    repo.search_menu_items_by_vector.return_value = []

    embeddings = AsyncMock()
    embeddings.get_embedding.return_value = [0.1] * 768

    retriever = HybridRetriever(
        repository=repo,
        embeddings_client=embeddings,
        min_score=0.65,
        evidence_threshold=0.72,
    )
    res = await retriever.retrieve("Quán có bán phở bò không?")
    assert res.has_sufficient_evidence is False
    assert res.items == []


def test_reranker_deduplicates_and_applies_multi_source_bonus():
    c1, _, _ = make_sample_chunks()
    reranker = HybridReranker(lexical_weight=0.08, multi_source_bonus=0.05, min_score=0.65)

    from src.rag.retrieval.vector_search import chunk_to_retrieved_item

    v_item = chunk_to_retrieved_item(c1, score=0.80, hop_type="vector")
    g_item = chunk_to_retrieved_item(c1, score=0.78, hop_type="next")

    ranked = reranker.rerank(
        query="Hạng Vàng 500 điểm",
        vector_items=[v_item],
        graph_items=[g_item],
        top_k=5,
    )
    assert len(ranked) == 1
    assert ranked[0].score > 0.85  # Base 0.80 + multi_source_bonus 0.05 + lexical overlap
