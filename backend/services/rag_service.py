"""Singleton RAG service that wraps DocumentRAGPipeline for the FastAPI backend."""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from dotenv import load_dotenv

from src.rag import DocumentRAGPipeline
from src.utils import combined_files_sha256, configure_logging

load_dotenv()

LOGGER = configure_logging()

CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:7b-instruct")
EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

MAX_FILE_SIZE_MB = 200
MAX_FILES_PER_UPLOAD = 10
ACCEPTED_SUFFIXES = frozenset({".pdf", ".docx", ".txt", ".md"})


class DocumentRecord:
    def __init__(self, doc_id: str, name: str, path: Path, size_bytes: int) -> None:
        self.id = doc_id
        self.name = name
        self.path = path
        self.size_bytes = size_bytes


class RAGService:
    """Holds pipeline + active-document state for the lifetime of the process."""

    def __init__(self) -> None:
        self._pipeline: Optional[DocumentRAGPipeline] = None
        self._documents: list[DocumentRecord] = []
        self._vectorstore: Any = None

    # ------------------------------------------------------------------
    # Lazy init
    # ------------------------------------------------------------------
    def _get_pipeline(self) -> DocumentRAGPipeline:
        if self._pipeline is None:
            LOGGER.info("Initialising RAG pipeline (chat=%s, embed=%s)", CHAT_MODEL, EMBEDDING_MODEL)
            self._pipeline = DocumentRAGPipeline(
                data_dir=Path("data"),
                persist_dir=Path("chroma_db"),
                chat_model=CHAT_MODEL,
                embedding_model=EMBEDDING_MODEL,
                logger=LOGGER,
            )
        return self._pipeline

    # ------------------------------------------------------------------
    # Document management
    # ------------------------------------------------------------------
    def list_documents(self) -> list[DocumentRecord]:
        return list(self._documents)

    def add_documents(self, files: list[tuple[str, bytes]]) -> list[DocumentRecord]:
        """Save files to disk, merge into the active set, and reindex."""
        if not files:
            raise ValueError("No files provided.")
        if len(self._documents) + len(files) > MAX_FILES_PER_UPLOAD:
            raise ValueError(
                f"Adding {len(files)} file(s) would exceed the {MAX_FILES_PER_UPLOAD}-file limit "
                f"({len(self._documents)} already active)."
            )

        pipeline = self._get_pipeline()
        saved_paths = pipeline.save_uploaded_documents(files)

        new_records: list[DocumentRecord] = []
        for path, (_, file_bytes) in zip(saved_paths, files):
            existing = next((d for d in self._documents if d.path == path), None)
            if existing:
                existing.size_bytes = len(file_bytes)
                new_records.append(existing)
            else:
                record = DocumentRecord(
                    doc_id=str(uuid.uuid4()),
                    name=path.name,
                    path=path,
                    size_bytes=len(file_bytes),
                )
                self._documents.append(record)
                new_records.append(record)

        self._reindex()
        return new_records

    def remove_document(self, doc_id: str) -> None:
        record = next((d for d in self._documents if d.id == doc_id), None)
        if record is None:
            raise KeyError(f"Document '{doc_id}' not found.")
        self._documents = [d for d in self._documents if d.id != doc_id]
        if self._documents:
            self._reindex()
        else:
            self._vectorstore = None

    def remove_all_documents(self) -> None:
        self._documents = []
        self._vectorstore = None

    def _reindex(self) -> None:
        paths = [d.path for d in self._documents]
        payloads = [(p.name, p.read_bytes()) for p in paths]
        file_hash = combined_files_sha256(payloads)
        self._vectorstore = self._get_pipeline().index_documents(paths, file_hash)
        LOGGER.info("Indexed %d document(s).", len(paths))

    # ------------------------------------------------------------------
    # Q&A + summary
    # ------------------------------------------------------------------
    def _resolve_active_sources(self, document_ids: list[str] | None) -> list[str]:
        source_names_all = [d.name for d in self._documents]
        if document_ids:
            selected = [d.name for d in self._documents if d.id in document_ids]
            return selected or source_names_all
        return source_names_all

    def answer_question(
        self,
        question: str,
        answer_mode: str = "standard",
        chat_history: list[dict] | None = None,
        document_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        if self._vectorstore is None:
            raise ValueError("No documents indexed. Upload documents first.")
        active_sources = self._resolve_active_sources(document_ids)
        return self._get_pipeline().answer_question(
            self._vectorstore,
            question,
            None,
            chat_history or [],
            answer_mode,
            source_filter=None,
            source_names=active_sources,
        )

    def prepare_answer(
        self,
        question: str,
        answer_mode: str = "standard",
        chat_history: list[dict] | None = None,
        document_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        if self._vectorstore is None:
            raise ValueError("No documents indexed. Upload documents first.")
        active_sources = self._resolve_active_sources(document_ids)
        return self._get_pipeline().prepare_answer(
            self._vectorstore,
            question,
            None,
            chat_history or [],
            answer_mode,
            source_filter=None,
            source_names=active_sources,
        )

    async def astream_answer(
        self, context: str, question: str, answer_mode: str
    ) -> AsyncIterator[str]:
        async for token in self._get_pipeline().astream_answer(
            context, question, answer_mode
        ):
            yield token

    def summarize(self) -> dict[str, Any]:
        if self._vectorstore is None:
            raise ValueError("No documents indexed. Upload documents first.")
        file_names = [d.name for d in self._documents]
        return self._get_pipeline().summarize_documents(self._vectorstore, file_names)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    @property
    def chat_model(self) -> str:
        return CHAT_MODEL

    @property
    def embedding_model(self) -> str:
        return EMBEDDING_MODEL


# Process-level singleton
rag_service = RAGService()
