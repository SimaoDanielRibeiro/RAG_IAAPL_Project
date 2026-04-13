"""Document loading helpers for supported file types."""

from __future__ import annotations

from pathlib import Path

from docx import Document as DocxFile
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


def load_source_documents(document_path: Path) -> list[Document]:
    """Load source content for supported document types."""
    suffix = document_path.suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(str(document_path)).load()
    if suffix == ".docx":
        return _load_docx_document(document_path)
    if suffix in {".txt", ".md"}:
        return _load_text_document(document_path)
    raise ValueError(f"Unsupported file type: '{document_path.suffix}'.")


def _load_docx_document(document_path: Path) -> list[Document]:
    """Load a DOCX file into a single LangChain document."""
    docx_file = DocxFile(str(document_path))
    paragraphs = [paragraph.text.strip() for paragraph in docx_file.paragraphs if paragraph.text.strip()]
    text = "\n\n".join(paragraphs)
    return [Document(page_content=text, metadata={"source": document_path.name})]


def _load_text_document(document_path: Path) -> list[Document]:
    """Load a TXT or Markdown file into a single LangChain document."""
    try:
        text = document_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = document_path.read_text(encoding="latin-1")
    return [Document(page_content=text, metadata={"source": document_path.name})]
