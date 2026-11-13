"""Unit tests for ChunkRecord, EntityRecord, and Neo4jRepository chunk/entity methods."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.rag.graph.client import Neo4jClient
from src.rag.graph.repository import Neo4jRepository
from src.schema.retrieval import ChunkRecord, EntityRecord


@pytest.fixture
def mock_driver():
    driver = MagicMock()
    driver.verify_connectivity = AsyncMock()
    driver.close = AsyncMock()
    return driver


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.run = AsyncMock()
    session.close = AsyncMock()
    return session


def test_chunk_and_entity_schemas_valid():
    chunk = ChunkRecord(
        chunk_id="faq-F001",
        source="faq",
        title="Wifi tên gì?",
        text="Hỏi: Wifi tên gì?\nĐáp: Highlands_Free",
        doc_id="faq",
        order=1,
        file="faq.csv",
        metadata={"category": "Tiện ích"},
    )
    assert chunk.chunk_id == "faq-F001"
    assert chunk.metadata["category"] == "Tiện ích"

    entity = EntityRecord(
        name="Highlands Cầu Giấy",
        entity_type="BRANCH",
        canonical_name="chi_nhanh_cau_giay",
    )
    assert entity.canonical_name == "chi_nhanh_cau_giay"
    assert entity.entity_type == "BRANCH"


async def test_init_chunk_schema_executes_queries(mock_driver, mock_session):
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    client = Neo4jClient(uri="neo4j+s://x", username="u", password="p")
    client._driver = mock_driver

    repo = Neo4jRepository(client)
    await repo.init_chunk_schema(vector_dimensions=768)

    assert mock_session.run.await_count >= 2


async def test_upsert_chunk(mock_driver, mock_session):
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_result = MagicMock()
    mock_result.single = AsyncMock(return_value={"chunk_id": "doc-policy-01"})
    mock_session.run.return_value = mock_result

    client = Neo4jClient(uri="neo4j+s://x", username="u", password="p")
    client._driver = mock_driver

    repo = Neo4jRepository(client)
    chunk = ChunkRecord(
        chunk_id="doc-policy-01",
        source="policy",
        title="Chính sách",
        text="Nội dung chính sách",
        doc_id="policy",
        order=1,
        file="policy.docx",
    )
    embedding = [0.1] * 768
    chunk_id = await repo.upsert_chunk(chunk, embedding)

    assert chunk_id == "doc-policy-01"
    assert mock_session.run.await_count == 1
    call_args = mock_session.run.await_args[1]
    assert call_args["chunk_id"] == "doc-policy-01"
    assert call_args["embedding"] == embedding


async def test_link_chunks_next(mock_driver, mock_session):
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    client = Neo4jClient(uri="neo4j+s://x", username="u", password="p")
    client._driver = mock_driver

    repo = Neo4jRepository(client)
    await repo.link_chunks_next("doc-policy-01", "doc-policy-02")

    assert mock_session.run.await_count == 1
    call_args = mock_session.run.await_args[1]
    assert call_args["c1_id"] == "doc-policy-01"
    assert call_args["c2_id"] == "doc-policy-02"


async def test_link_chunk_mentions(mock_driver, mock_session):
    mock_driver.session = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session

    client = Neo4jClient(uri="neo4j+s://x", username="u", password="p")
    client._driver = mock_driver

    repo = Neo4jRepository(client)
    entity = EntityRecord(
        name="Chi nhánh Cầu Giấy",
        entity_type="BRANCH",
        canonical_name="chi_nhanh_cau_giay",
    )
    await repo.link_chunk_mentions("doc-branch-01", entity)

    assert mock_session.run.await_count == 1
    call_args = mock_session.run.await_args[1]
    assert call_args["chunk_id"] == "doc-branch-01"
    assert call_args["canonical_name"] == "chi_nhanh_cau_giay"
