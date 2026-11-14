"""Unit tests for FAQ parser and FAQIngestor."""

from pathlib import Path
from unittest.mock import AsyncMock

from src.rag.ingestion.faq import FAQIngestor, parse_faq_row


def test_parse_faq_row_formats_chunk_record():
    row = {
        "faq_id": "F001",
        "topic_id": "wifi",
        "category": "Tiện ích",
        "language": "vi",
        "question": "Wifi tên gì vậy?",
        "answer": "Wifi của quán tên là Highlands_Free ạ.",
    }
    chunk = parse_faq_row(row)
    assert chunk.chunk_id == "faq-F001"
    assert chunk.source == "faq"
    assert chunk.title == "Wifi tên gì vậy?"
    assert chunk.text == "Hỏi: Wifi tên gì vậy?\nĐáp: Wifi của quán tên là Highlands_Free ạ."
    assert chunk.doc_id == "faq"
    assert chunk.file == "faq.csv"
    assert chunk.metadata == {"topic_id": "wifi", "category": "Tiện ích", "language": "vi"}


async def test_faq_ingestor_flow(tmp_path: Path):
    csv_file = tmp_path / "test_faq.csv"
    csv_file.write_text(
        "faq_id,topic_id,category,language,question,answer\n"
        "F001,wifi,Tiện ích,vi,Wifi tên gì?,Highlands_Free\n"
        "F002,hours,Giờ,vi,Mấy giờ mở?,Mở từ 7h\n",
        encoding="utf-8",
    )

    mock_repo = AsyncMock()
    mock_repo.upsert_chunk.return_value = "faq-id"

    mock_embeddings = AsyncMock()
    mock_embeddings.get_embeddings_batch.return_value = [[0.1] * 768, [0.2] * 768]

    ingestor = FAQIngestor(
        csv_path=csv_file,
        repository=mock_repo,
        embeddings_client=mock_embeddings,
        batch_size=2,
    )
    count = await ingestor.ingest()

    assert count == 2
    assert mock_embeddings.get_embeddings_batch.await_count == 1
    assert mock_repo.upsert_chunk.await_count == 2

