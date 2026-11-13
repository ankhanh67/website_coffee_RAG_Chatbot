"""Unit tests for InboxWatcher file processing."""

from pathlib import Path
from unittest.mock import AsyncMock

from src.rag.ingestion.watcher import InboxWatcher


async def test_inbox_watcher_processes_csv_and_docx(tmp_path: Path):
    inbox_dir = tmp_path / "inbox"
    inbox_dir.mkdir()

    mock_repo = AsyncMock()
    mock_repo.upsert_chunk.return_value = "chunk-id"
    mock_repo.upsert_menu_item.return_value = "item-id"

    mock_embeddings = AsyncMock()
    mock_embeddings.get_embeddings_batch.return_value = [[0.1] * 768]

    mock_extractor = AsyncMock()
    mock_extractor.extract_entities.return_value = []

    watcher = InboxWatcher(
        inbox_dir=inbox_dir,
        repository=mock_repo,
        embeddings_client=mock_embeddings,
        entity_extractor=mock_extractor,
    )

    # Test processing a newly dropped FAQ csv
    faq_file = inbox_dir / "new_faq.csv"
    faq_file.write_text(
        "faq_id,topic_id,category,language,question,answer\n"
        "F999,test,Test,vi,Câu hỏi mới?,Trả lời mới\n",
        encoding="utf-8",
    )
    count = await watcher.process_file(faq_file)
    assert count == 1
    assert mock_repo.upsert_chunk.await_count == 1

