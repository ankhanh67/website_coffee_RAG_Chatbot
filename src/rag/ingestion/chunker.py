"""Chunker for loading manifest sections and parsing raw docx/pdf documents."""

import json
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from src.schema.retrieval import ChunkRecord


class DocumentChunker:
    @staticmethod
    def load_manifest(path: Path) -> list[ChunkRecord]:
        with Path(path).open(encoding="utf-8") as f:
            data = json.load(f)

        chunks: list[ChunkRecord] = []
        for item in data:
            sec_id = item["section_id"].strip()
            heading = item.get("heading", "").strip()
            body = item.get("text", "").strip()
            text = f"{heading}\n{body}" if heading else body

            chunks.append(
                ChunkRecord(
                    chunk_id=f"doc-{sec_id}",
                    source=item.get("doc_id", "document").strip(),
                    title=heading or sec_id,
                    text=text,
                    doc_id=item.get("doc_id", "").strip(),
                    order=int(item.get("order", 0)),
                    file=item.get("file", "").strip(),
                    metadata={"section_id": sec_id},
                )
            )
        return chunks

    @staticmethod
    def parse_docx(path: Path, doc_id: str = "custom") -> list[ChunkRecord]:
        doc = Document(str(path))
        chunks: list[ChunkRecord] = []
        current_heading = path.stem
        order = 1

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            if para.style.name.startswith("Heading"):
                current_heading = text
                continue

            chunk_id = f"doc-{doc_id}-{order:02d}"
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    source=doc_id,
                    title=current_heading,
                    text=f"{current_heading}\n{text}",
                    doc_id=doc_id,
                    order=order,
                    file=path.name,
                )
            )
            order += 1
        return chunks

    @staticmethod
    def parse_pdf(path: Path, doc_id: str = "custom") -> list[ChunkRecord]:
        reader = PdfReader(str(path))
        chunks: list[ChunkRecord] = []
        order = 1

        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if not text:
                continue

            chunk_id = f"doc-{doc_id}-p{idx:02d}"
            title = f"{path.stem} (Trang {idx})"
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    source=doc_id,
                    title=title,
                    text=f"{title}\n{text}",
                    doc_id=doc_id,
                    order=order,
                    file=path.name,
                )
            )
            order += 1
        return chunks
