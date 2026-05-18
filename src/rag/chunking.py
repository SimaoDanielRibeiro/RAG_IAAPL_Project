"""Document chunking and metadata enrichment.

PDFs use a heading-aware chunker that respects the structural markers
produced by ``pdf_extractor`` (``# `` headings, ``[Caption] ``, markdown
tables). DOCX / TXT / MD fall back to a recursive character splitter
since they don't carry layout signals through the loader.
"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.rag.config import RAGConfig
from src.rag.document_loader import load_source_documents


_NEIGHBOR_NONE_SENTINEL = -1

_HEADING_PREFIX = "# "
_CAPTION_PREFIX = "[Caption] "


class DocumentChunker:
    """Load source files and split them into indexed chunks with metadata.

    Each chunk receives:
    - `source` — original file name
    - `page` — 0-based page number (preserved from the loader)
    - `chunk_index` — position in source (0-based)
    - `chunk_size` — character count
    - `previous_chunk_index`, `next_chunk_index` — for neighbor expansion
      (use -1 to indicate "no neighbor"; Chroma stores ints natively but
      None handling is inconsistent across versions).
    - `section_title` — for PDFs, the most recent heading seen by the
      chunker; for other formats, a heuristic from the chunk's first line.
    - `content_type` — "table" when the chunk consists primarily of a
      markdown table, otherwise "text".
    """

    def __init__(self, config: RAGConfig) -> None:
        self.config = config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=list(config.chunk_separators),
        )
        # Heading-aware chunks can be a bit larger because they end on
        # semantic boundaries; a hard ceiling stops a runaway dense section
        # from producing one giant chunk that overwhelms the reranker.
        self._heading_target_size = config.chunk_size * 2
        self._heading_hard_max    = config.chunk_size * 3
        self._heading_min_flush   = config.chunk_size // 2

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

        if document_path.suffix.lower() == ".pdf":
            chunks = self._chunk_pdf_heading_aware(loaded_documents)
        else:
            chunks = self.text_splitter.split_documents(loaded_documents)

        if not chunks:
            raise ValueError(f"No text chunks could be created from '{document_path.name}'.")

        return self._add_chunk_metadata(chunks, document_path.name)

    # ------------------------------------------------------------------
    # PDF heading-aware chunking
    # ------------------------------------------------------------------
    def _chunk_pdf_heading_aware(self, pages: list[Document]) -> list[Document]:
        """Walk paragraphs across pages, packing chunks on heading boundaries.

        A 'paragraph' is a blank-line-delimited block produced by
        ``pdf_extractor``. Headings (`# ...`) trigger a flush when the
        current buffer has enough content, so each chunk tends to start at
        a section boundary. Tables and oversized paragraphs are emitted as
        their own chunks so the markdown structure stays intact.
        """
        chunks: list[Document] = []

        buffer_text:    str = ""
        buffer_page:    int = pages[0].metadata.get("page", 0) if pages else 0
        buffer_section: str = ""
        buffer_is_table: bool = False
        current_section: str = ""

        def flush() -> None:
            nonlocal buffer_text, buffer_is_table
            text = buffer_text.strip()
            if text:
                chunks.append(
                    Document(
                        page_content=text,
                        metadata={
                            "page":          buffer_page,
                            "section_title": buffer_section,
                            "content_type":  "table" if buffer_is_table else "text",
                        },
                    )
                )
            buffer_text     = ""
            buffer_is_table = False

        def start_buffer(text: str, page: int, is_table: bool = False) -> None:
            nonlocal buffer_text, buffer_page, buffer_section, buffer_is_table
            buffer_text     = text
            buffer_page     = page
            buffer_section  = current_section
            buffer_is_table = is_table

        def append_to_buffer(text: str) -> None:
            nonlocal buffer_text
            buffer_text = f"{buffer_text}\n\n{text}" if buffer_text else text

        for page_doc in pages:
            page_num = page_doc.metadata.get("page", 0)
            for paragraph in _split_paragraphs(page_doc.page_content):
                is_heading = paragraph.startswith(_HEADING_PREFIX)
                is_table   = paragraph.startswith("|") and "\n" in paragraph and "---" in paragraph

                if is_heading:
                    heading_text = _normalize_whitespace(
                        paragraph[len(_HEADING_PREFIX):]
                    )
                    if len(buffer_text) >= self._heading_min_flush:
                        flush()
                    current_section = heading_text or current_section
                    if not buffer_text:
                        start_buffer(paragraph, page_num)
                    else:
                        append_to_buffer(paragraph)
                    continue

                if is_table:
                    # Tables stand alone so their markdown structure survives.
                    if buffer_text:
                        flush()
                    start_buffer(paragraph, page_num, is_table=True)
                    flush()
                    continue

                paragraph_len = len(paragraph)
                projected     = len(buffer_text) + paragraph_len + 2

                if (
                    projected > self._heading_target_size
                    and len(buffer_text) >= self._heading_min_flush
                ):
                    flush()

                if not buffer_text:
                    start_buffer(paragraph, page_num)
                else:
                    append_to_buffer(paragraph)

                # Hard ceiling: if a single section runs long, force a flush.
                if len(buffer_text) >= self._heading_hard_max:
                    flush()

        flush()
        return chunks

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def _add_chunk_metadata(self, chunks: list[Document], source_name: str) -> list[Document]:
        """Attach metadata that retrieval, citations, and neighbor expansion need."""
        total_chunks = len(chunks)
        documents: list[Document] = []
        for index, chunk in enumerate(chunks):
            metadata = dict(chunk.metadata)
            metadata["source"]      = source_name
            metadata["chunk_index"] = index
            metadata["chunk_size"]  = len(chunk.page_content)
            metadata["previous_chunk_index"] = (
                index - 1 if index > 0 else _NEIGHBOR_NONE_SENTINEL
            )
            metadata["next_chunk_index"] = (
                index + 1 if index < total_chunks - 1 else _NEIGHBOR_NONE_SENTINEL
            )
            # Don't overwrite a section_title the heading-aware chunker set.
            if not metadata.get("section_title"):
                metadata["section_title"] = self._detect_section_title(chunk.page_content) or ""
            metadata.setdefault("content_type", "text")
            documents.append(Document(page_content=chunk.page_content, metadata=metadata))
        return documents

    @staticmethod
    def _detect_section_title(chunk_text: str) -> str | None:
        """Heuristically detect a heading-like first line in a chunk."""
        for raw_line in chunk_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            # Recognise the explicit markers from pdf_extractor first.
            if line.startswith(_HEADING_PREFIX):
                return line[len(_HEADING_PREFIX):].strip() or None
            if line.startswith(_CAPTION_PREFIX):
                return None
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


def _split_paragraphs(page_text: str) -> list[str]:
    """Split a structured page string into the paragraphs the chunker walks.

    Blank lines separate blocks; markdown tables stay intact because their
    rows are joined with single newlines, not double.
    """
    blocks = re.split(r"\n{2,}", page_text)
    return [block.strip() for block in blocks if block and block.strip()]


def _normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace (incl. newlines) into single spaces."""
    return " ".join(text.split())
