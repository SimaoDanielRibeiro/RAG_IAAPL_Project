"""Document chunking and metadata enrichment."""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.rag.config import RAGConfig
from src.rag.document_loader import load_source_documents


_NEIGHBOR_NONE_SENTINEL = -1


class DocumentChunker:
    """Load source files and split them into indexed chunks with metadata.

    Each chunk receives:
    - `source` — original file name
    - `chunk_index` — position in source (0-based)
    - `chunk_size` — character count
    - `previous_chunk_index`, `next_chunk_index` — for neighbor expansion
      (use -1 to indicate "no neighbor"; Chroma stores ints natively but
      None handling is inconsistent across versions).
    - `section_title` — heuristic heading detected from the chunk's first line.
    """

    def __init__(self, config: RAGConfig) -> None:
        self.config = config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=list(config.chunk_separators),
        )

    def prepare_for_indexing(self, document_path: Path) -> list[Document]:
        """Load a document, split it, and attach deterministic metadata.

        Raises:
            ValueError: If no readable text is found, or if splitting yields
                no chunks (e.g., scanned PDF without OCR).
        """
        loaded_documents = load_source_documents(document_path)
        extracted_text = " ".join(
            document.page_content.strip()
            for document in loaded_documents
            if document.page_content.strip()
        )
        if not extracted_text:
            raise ValueError(
                f"No readable text was extracted from '{document_path.name}'. "
                "If it is scanned, OCR may be required before upload."
            )

        chunks = self.text_splitter.split_documents(loaded_documents)
        if not chunks:
            raise ValueError(f"No text chunks could be created from '{document_path.name}'.")

        return self._add_chunk_metadata(chunks, document_path.name)

    def _add_chunk_metadata(self, chunks: list[Document], source_name: str) -> list[Document]:
        """Attach metadata that retrieval, citations, and neighbor expansion need."""
        total_chunks = len(chunks)
        documents: list[Document] = []
        for index, chunk in enumerate(chunks):
            metadata = dict(chunk.metadata)
            metadata["source"] = source_name
            metadata["chunk_index"] = index
            metadata["chunk_size"] = len(chunk.page_content)
            metadata["previous_chunk_index"] = (
                index - 1 if index > 0 else _NEIGHBOR_NONE_SENTINEL
            )
            metadata["next_chunk_index"] = (
                index + 1 if index < total_chunks - 1 else _NEIGHBOR_NONE_SENTINEL
            )
            metadata["section_title"] = self._detect_section_title(chunk.page_content) or ""
            documents.append(Document(page_content=chunk.page_content, metadata=metadata))
        return documents

    @staticmethod
    def _detect_section_title(chunk_text: str) -> str | None:
        """Heuristically detect a heading-like first line in a chunk."""
        for raw_line in chunk_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if len(line) > 80:
                return None
            if line.isupper():
                return line
            if re.match(r"^\d+(\.\d+)*\s+[A-Z].*", line):
                return line
            if line == line.title() and len(line.split()) <= 10:
                return line
            return None
        return None
