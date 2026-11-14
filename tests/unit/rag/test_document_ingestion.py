"""Unit tests for DocumentChunker and DocumentIngestor."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

from src.rag.ingestion.chunker import DocumentChunker
from src.rag.ingestion.document import DocumentIngestor
from src.schema.retrieval import EntityRecord


def test_chunker_loads_manifest_sections(tmp_path: Path):
    manifest_file = tmp_path / "manifest.json"
    manifest_data = [
        {
            "section_id": "policy-01",
            "doc_id": "policy",
            "file": "policy.docx",
            "order": 1,
            "heading": "Mục đích",
            "text": "Quy định phục vụ khách hàng.",
        },
        {
            "section_id": "policy-02",
            "doc_id": "policy",
            "file": "policy.docx",
            "order": 2,
            "heading": "Làm lại món",
            "text": "Làm lại món trong vòng 15 phút.",
        },
    ]
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    chunks = DocumentChunker.load_manifest(manifest_file)
    assert len(chunks) == 2
    assert chunks[0].chunk_id == "doc-policy-01"
    assert chunks[0].order == 1
    assert chunks[0].title == "Mục đích"
    assert "Quy định phục vụ" in chunks[0].text
    assert chunks[1].chunk_id == "doc-policy-02"
    assert chunks[1].order == 2


async def test_document_ingestor_creates_chunks_next_and_mentions(tmp_path: Path):
    manifest_file = tmp_path / "manifest.json"
    manifest_data = [
        {
            "section_id": "branch-01",
            "doc_id": "branch",
            "file": "branch.pdf",
            "order": 1,
            "heading": "Chi nhánh Cầu Giấy",
            "text": "Chi nhánh Cầu Giấy mở cửa 7h-22h.",
        },
        {
            "section_id": "branch-02",
            "doc_id": "branch",
            "file": "branch.pdf",
            "order": 2,
            "heading": "Chi nhánh Bạch Đằng",
            "text": "Chi nhánh Bạch Đằng mở cửa 7h-23h.",
        },
    ]
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    mock_repo = AsyncMock()
    mock_repo.upsert_chunk.return_value = "doc-id"
    mock_repo.link_chunks_next = AsyncMock()
    mock_repo.link_chunk_mentions = AsyncMock()

    mock_embeddings = AsyncMock()
    mock_embeddings.get_embeddings_batch.return_value = [[0.1] * 768, [0.2] * 768]

    mock_extractor = AsyncMock()
    mock_extractor.extract_entities.return_value = [
        EntityRecord(name="Chi nhánh Cầu Giấy", entity_type="BRANCH", canonical_name="branch_cau_giay")
    ]

    ingestor = DocumentIngestor(
        manifest_path=manifest_file,
        repository=mock_repo,
        embeddings_client=mock_embeddings,
        entity_extractor=mock_extractor,
        batch_size=2,
    )
    count = await ingestor.ingest()

    assert count == 2
    assert mock_repo.upsert_chunk.await_count == 2
    # Verify [:NEXT] was linked between branch-01 and branch-02
    assert mock_repo.link_chunks_next.await_count == 1
    mock_repo.link_chunks_next.assert_awaited_with("doc-branch-01", "doc-branch-02")
    # Verify [:MENTIONS] was linked
    assert mock_repo.link_chunk_mentions.await_count >= 1

