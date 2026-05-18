"""Document loading helpers for supported file types."""

from __future__ import annotations

import logging
from pathlib import Path

from docx import Document as DocxFile
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from src.rag.pdf_extractor import extract_pages as _pymupdf_extract_pages


SUPPORTED_SUFFIXES: frozenset[str] = frozenset({".pdf", ".docx", ".txt", ".md"})

LOGGER = logging.getLogger(__name__)


def load_source_documents(document_path: Path) -> list[Document]:
    """Load source content for supported document types.

    Args:
        document_path: Local path to the document file.

    Returns:
        A list of LangChain `Document` objects. PDFs use the layout-aware
        PyMuPDF extractor (one Document per page with structured text:
        ``# `` heading markers, ``[Caption] `` prefixes, markdown tables).
        DOCX/TXT/MD return a single document with the full text.

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the file extension is unsupported.
    """
    if not document_path.exists():
        raise FileNotFoundError(f"Document not found: '{document_path}'.")

    suffix = document_path.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf_document(document_path)
    if suffix == ".docx":
        return _load_docx_document(document_path)
    if suffix in {".txt", ".md"}:
        return _load_text_document(document_path)

    raise ValueError(
        f"Unsupported file type: '{document_path.suffix}'. "
        f"Supported types: {sorted(SUPPORTED_SUFFIXES)}."
    )


def _load_pdf_document(document_path: Path) -> list[Document]:
    """Layout-aware PDF loader.

    Falls back to ``PyPDFLoader`` if PyMuPDF can't produce any text
    (encrypted PDFs, vector-only pages, etc.), so the pipeline still has
    something to index.
    """
    try:
        pages = _pymupdf_extract_pages(document_path)
    except Exception:
        LOGGER.exception(
            "PyMuPDF extraction failed for %s; falling back to PyPDFLoader.",
            document_path.name,
        )
        return PyPDFLoader(str(document_path)).load()

    documents = [
        Document(
            page_content=text,
            metadata={"source": document_path.name, "page": page_index},
        )
        for page_index, text in enumerate(pages)
        if text and text.strip()
    ]
    if not documents:
        LOGGER.warning(
            "PyMuPDF returned no text for %s; falling back to PyPDFLoader.",
            document_path.name,
        )
        return PyPDFLoader(str(document_path)).load()
    return documents


def _load_docx_document(document_path: Path) -> list[Document]:
    """Load a DOCX file into a single LangChain document."""
    docx_file = DocxFile(str(document_path))
    paragraphs = [
        paragraph.text.strip()
        for paragraph in docx_file.paragraphs
        if paragraph.text.strip()
    ]
    text = "\n\n".join(paragraphs)
    return [Document(page_content=text, metadata={"source": document_path.name})]


def _load_text_document(document_path: Path) -> list[Document]:
    """Load a TXT or Markdown file into a single LangChain document."""
    try:
        text = document_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = document_path.read_text(encoding="latin-1")
    return [Document(page_content=text, metadata={"source": document_path.name})]
