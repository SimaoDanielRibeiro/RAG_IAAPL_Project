"""Chroma vector store setup and manifest management."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from src.rag.config import RAGConfig
from src.utils import load_json_file, save_json_file


def safe_collection_name(file_name: str, content_hash: str) -> str:
    """Build a stable, filesystem-safe Chroma collection name.

    Format: ``<sanitized-stem-truncated-to-40>-<first-12-of-hash>``.
    The 12-character hash suffix is enough to collision-avoid in practice.
    """
    stem = Path(file_name).stem.lower()
    cleaned = "".join(character if character.isalnum() else "-" for character in stem)
    cleaned = cleaned.strip("-") or "document"
    return f"{cleaned[:40]}-{content_hash[:12]}"


class VectorStoreManager:
    """Create, reuse, and record Chroma collections.

    Responsibilities:
    - Open a Chroma collection by name (creating if missing).
    - Detect whether a collection already has indexed chunks (avoids re-indexing).
    - Persist a manifest of (content_hash, config) → collection_name so the
      app can reuse collections across reruns and restarts.
    """

    def __init__(
        self,
        persist_dir: Path,
        manifest_path: Path,
        embeddings: OllamaEmbeddings,
        embedding_model_name: str,
        chat_model_name: str,
        reranker_model_name: str,
        config: RAGConfig,
        logger: logging.Logger,
    ) -> None:
        self.persist_dir = persist_dir
        self.manifest_path = manifest_path
        self.embeddings = embeddings
        self.embedding_model_name = embedding_model_name
        self.chat_model_name = chat_model_name
        self.reranker_model_name = reranker_model_name
        self.config = config
        self.logger = logger

    def create_or_reuse(
        self,
        document_paths: list[Path],
        content_hash: str,
        chunks_by_path: dict[Path, list[Document]],
    ) -> Chroma:
        """Create a Chroma collection, or reuse one that already holds these documents."""
        if not document_paths:
            raise ValueError("At least one document is required for indexing.")

        collection_seed = (
            document_paths[0].name if len(document_paths) == 1 else "multi-document-set"
        )
        collection_name = self.resolve_collection_name(collection_seed, content_hash)
        vectorstore = self.open_collection(collection_name)

        if self.collection_has_documents(vectorstore):
            self.logger.info("Reusing existing Chroma collection '%s'", collection_name)
            return vectorstore

        all_chunks: list[Document] = []
        for document_path in document_paths:
            all_chunks.extend(chunks_by_path[document_path])
        if not all_chunks:
            raise ValueError("No chunks were produced for indexing.")

        vectorstore.add_documents(all_chunks)
        self.save_manifest_entry(
            file_names=[document_path.name for document_path in document_paths],
            content_hash=content_hash,
            collection_name=collection_name,
            chunk_count=len(all_chunks),
        )
        self.logger.info(
            "Indexed %s chunks into collection '%s'", len(all_chunks), collection_name
        )
        return vectorstore

    def open_collection(self, collection_name: str) -> Chroma:
        """Open a Chroma collection with the configured embeddings."""
        return Chroma(
            collection_name=collection_name,
            persist_directory=str(self.persist_dir),
            embedding_function=self.embeddings,
        )

    def collection_has_documents(self, vectorstore: Chroma) -> bool:
        """Check if a Chroma collection has any chunks without using private attributes."""
        try:
            result = vectorstore.get(limit=1, include=[])
        except TypeError:
            # Older langchain-chroma versions don't support `limit`.
            result = vectorstore.get(include=[])
        return bool(result.get("ids", []))

    def resolve_collection_name(self, file_name: str, content_hash: str) -> str:
        """Reuse the stored collection name for this document set when available.

        Lookup order:
        1. New-style key ``<content_hash>:<index_config_hash>`` — preferred.
        2. Legacy key (just ``<content_hash>``) when the embedding model still matches.
        3. Otherwise, derive a fresh name.
        """
        manifest = load_json_file(self.manifest_path)
        entry = manifest.get(self.manifest_key(content_hash))
        if entry:
            return entry["collection_name"]

        legacy_entry = manifest.get(content_hash)
        if legacy_entry and legacy_entry.get("embedding_model") == self.embedding_model_name:
            return legacy_entry["collection_name"]

        collection_hash = hashlib.sha256(
            f"{content_hash}{self.index_config_hash()}".encode("utf-8")
        ).hexdigest()
        return safe_collection_name(file_name, collection_hash)

    def save_manifest_entry(
        self,
        file_names: list[str],
        content_hash: str,
        collection_name: str,
        chunk_count: int,
    ) -> None:
        """Persist indexing metadata for reuse and debugging."""
        manifest = load_json_file(self.manifest_path)
        manifest[self.manifest_key(content_hash)] = {
            "file_names": file_names,
            "collection_name": collection_name,
            "chunk_count": chunk_count,
            "chat_model": self.chat_model_name,
            "embedding_model": self.embedding_model_name,
            "reranker_model": self.reranker_model_name,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "index_version": self.config.index_version,
        }
        save_json_file(self.manifest_path, manifest)

    def manifest_key(self, content_hash: str) -> str:
        """Build a manifest key that changes when indexing configuration changes."""
        return f"{content_hash}:{self.index_config_hash()}"

    def index_config_hash(self) -> str:
        """Hash the settings that affect stored embeddings and chunk layout."""
        payload = "|".join(
            [
                self.embedding_model_name,
                str(self.config.chunk_size),
                str(self.config.chunk_overlap),
                ",".join(self.config.chunk_separators),
                self.config.index_version,
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
