"""Unit tests for Jaccard token similarity, EntityDeduplicator, and EntityExtractor."""

from unittest.mock import AsyncMock

from src.rag.ingestion.entity_deduplicator import (
    EntityDeduplicator,
    jaccard_token_similarity,
)
from src.rag.ingestion.entity_extractor import EntityExtractor, ExtractedEntitiesResult
from src.schema.retrieval import EntityRecord


def test_jaccard_token_similarity():
    sim1 = jaccard_token_similarity("Highlands Cầu Giấy", "Chi nhánh Cầu Giấy")
    assert sim1 >= 0.5  # "cầu", "giấy" match

    sim2 = jaccard_token_similarity("Chi nhánh Cầu Giấy", "Chi nhánh Cầu Giấy")
    assert sim2 == 1.0

    sim3 = jaccard_token_similarity("Nguyễn Huệ", "Cầu Giấy")
    assert sim3 == 0.0


def test_entity_deduplicator_merges_variations():
    dedup = EntityDeduplicator(threshold=0.5)

    e1 = dedup.deduplicate("Chi nhánh Cầu Giấy", "BRANCH")
    assert e1.canonical_name == "branch_cau_giay"

    # Variation "Highlands Cầu Giấy" should deduplicate to "branch_cau_giay"
    e2 = dedup.deduplicate("Highlands Cầu Giấy", "BRANCH")
    assert e2.canonical_name == "branch_cau_giay"

    # Different branch
    e3 = dedup.deduplicate("Chi nhánh Nguyễn Huệ", "BRANCH")
    assert e3.canonical_name == "branch_nguyen_hue"
    assert e3.canonical_name != e1.canonical_name


async def test_entity_extractor_extracts_branches_payments_and_promos():
    mock_model_client = AsyncMock()
    mock_model_client.generate_structured.return_value = ExtractedEntitiesResult(
        entities=[
            EntityRecord(name="Chi nhánh Cầu Giấy", entity_type="BRANCH", canonical_name="branch_cau_giay"),
            EntityRecord(name="Chi nhánh Bạch Đằng", entity_type="BRANCH", canonical_name="branch_bach_dang"),
            EntityRecord(name="Ví MoMo", entity_type="PAYMENT", canonical_name="payment_momo"),
            EntityRecord(name="ZaloPay", entity_type="PAYMENT", canonical_name="payment_zalopay"),
            EntityRecord(name="Mã giảm giá HLT50", entity_type="PROMOTION", canonical_name="promo_hlt50"),
        ]
    )

    extractor = EntityExtractor(model_client=mock_model_client)
    sample_text = (
        "Khách hàng tại chi nhánh Cầu Giấy và chi nhánh Bạch Đằng có thể thanh toán qua ví MoMo "
        "hoặc ZaloPay để nhận mã giảm giá HLT50."
    )
    entities = await extractor.extract_entities(sample_text)
    assert mock_model_client.generate_structured.await_count == 1
    names = {e.canonical_name for e in entities}

    assert "branch_cau_giay" in names
    assert "branch_bach_dang" in names
    assert "payment_momo" in names
    assert "payment_zalopay" in names
    assert any(e.entity_type == "PROMOTION" and "hlt50" in e.canonical_name for e in entities)
