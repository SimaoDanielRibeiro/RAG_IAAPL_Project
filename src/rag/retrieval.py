"""Hybrid retrieval over Chroma vector search and BM25 keyword search."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.rag.config import RAGConfig

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None


_NEIGHBOR_NONE_SENTINEL = -1


@dataclass
class _BM25CacheEntry:
    """Cached BM25 index for one Chroma collection."""

    cache_key: str
    documents: list[Document]
    bm25: Any


class HybridRetriever:
    """Retrieve candidate chunks using semantic and keyword search.

    Vector retrieval provides semantic recall; BM25 keyword retrieval catches
    rare-term matches the embedding model misses. Their results are
    concatenated; downstream deduplication and reranking decide what survives.

    BM25 is built lazily per collection and cached. The cache key is derived
    from a stable Chroma attribute (collection name) rather than `id(...)`
    so it survives Streamlit's pipeline-level reruns.
    """

    def __init__(self, config: RAGConfig, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        self._bm25_cache: dict[str, _BM25CacheEntry] = {}

    # ------------------------------------------------------------------
    # Public retrieval entry points
    # ------------------------------------------------------------------
    def retrieve(
        self,
        vectorstore: Chroma,
        queries: list[str],
        top_k: int,
        source_filter: str | None = None,
    ) -> list[Document]:
        """Combine semantic MMR retrieval with BM25 keyword retrieval."""
        vector_documents = self.retrieve_vector(vectorstore, queries, top_k=top_k, source_filter=source_filter)
        keyword_documents = self.retrieve_keyword(vectorstore, queries, top_k=top_k, source_filter=source_filter)
        return vector_documents + keyword_documents

    def retrieve_diverse(
        self,
        vectorstore: Chroma,
        queries: list[str],
        top_k: int,
        source_names: list[str],
    ) -> list[Document]:
        """Per-source retrieval followed by global merge for better multi-file coverage.

        Retrieves candidates from each source independently so no single large
        document crowds out smaller ones. The caller deduplicates and reranks
        the merged pool globally.
        """
        if not source_names:
            return self.retrieve(vectorstore, queries, top_k=top_k)
        per_source_k = max(3, (top_k // len(source_names)) + 1)
        all_docs: list[Document] = []
        for source in source_names:
            vec_docs = self.retrieve_vector(vectorstore, queries, top_k=per_source_k, source_filter=source)
            kw_docs = self.retrieve_keyword(vectorstore, queries, top_k=per_source_k, source_filter=source)
            all_docs.extend(vec_docs)
            all_docs.extend(kw_docs)
        return all_docs

    def retrieve_vector(
        self,
        vectorstore: Chroma,
        queries: list[str],
        top_k: int,
        source_filter: str | None = None,
    ) -> list[Document]:
        """Run MMR vector retrieval for each query variant."""
        retrieved_documents: list[Document] = []
        fetch_k = max(
            top_k * self.config.vector_fetch_multiplier,
            self.config.vector_fetch_k_minimum,
        )
        chroma_filter = {"source": source_filter} if source_filter else None
        for query in queries:
            try:
                kwargs: dict = dict(
                    query=query,
                    k=top_k,
                    fetch_k=fetch_k,
                    lambda_mult=self.config.mmr_lambda,
                )
                if chroma_filter:
                    kwargs["filter"] = chroma_filter
                results = vectorstore.max_marginal_relevance_search(**kwargs)
            except Exception as error:
                self.logger.warning(
                    "Vector retrieval failed for query '%s'. Error: %s", query, error
                )
                continue
            for document in results:
                retrieved_documents.append(self._tag_method(document, "vector"))
        return retrieved_documents

    def retrieve_keyword(
        self,
        vectorstore: Chroma,
        queries: list[str],
        top_k: int,
        source_filter: str | None = None,
    ) -> list[Document]:
        """Run BM25 keyword retrieval over chunks already stored in Chroma."""
        if BM25Okapi is None:
            self.logger.info(
                "rank-bm25 is not installed; skipping keyword retrieval. "
                "Install it to enable hybrid search."
            )
            return []

        entry = self._get_bm25_entry(vectorstore)
        if entry is None:
            return []

        # When filtering by source, build an on-the-fly subset index.
        if source_filter:
            docs = [d for d in entry.documents if d.metadata.get("source") == source_filter]
            if not docs:
                return []
            tokenized_corpus = [self._tokenize(d.page_content) for d in docs]
            bm25 = BM25Okapi(tokenized_corpus)
        else:
            docs = entry.documents
            bm25 = entry.bm25

        retrieved_documents: list[Document] = []
        for query in queries:
            query_tokens = self._tokenize(query)
            if not query_tokens:
                continue

            scores = bm25.get_scores(query_tokens)
            if not len(scores):
                continue

            ranked_indexes = sorted(
                range(len(scores)), key=lambda index: scores[index], reverse=True
            )[:top_k]

            for index in ranked_indexes:
                if scores[index] <= 0:
                    continue
                document = docs[index]
                tagged = self._tag_method(document, "keyword")
                tagged.metadata["bm25_score"] = round(float(scores[index]), 4)
                retrieved_documents.append(tagged)
        return retrieved_documents

    def expand_neighbor_chunks(
        self, vectorstore: Chroma, documents: list[Document]
    ) -> list[Document]:
        """Include previous and next chunks for retrieved results when available."""
        expanded_documents: list[Document] = list(documents)
        for document in documents:
            source = document.metadata.get("source")
            neighbor_indexes = (
                document.metadata.get("previous_chunk_index"),
                document.metadata.get("next_chunk_index"),
            )
            for chunk_index in neighbor_indexes:
                if not source or chunk_index is None:
                    continue
                if int(chunk_index) <= _NEIGHBOR_NONE_SENTINEL:
                    continue
                neighbor = self.load_chunk_by_index(vectorstore, str(source), int(chunk_index))
                if neighbor is not None:
                    expanded_documents.append(neighbor)
        return deduplicate_documents(expanded_documents)

    # ------------------------------------------------------------------
    # Source-level helpers used by summarization
    # ------------------------------------------------------------------
    def get_all_indexed_documents(self, vectorstore: Chroma) -> list[Document]:
        """Load every indexed chunk from Chroma."""
        result = vectorstore.get(include=["documents", "metadatas"])
        documents = result.get("documents", []) or []
        metadatas = result.get("metadatas", []) or []
        return [
            Document(page_content=page_content, metadata=metadata or {})
            for page_content, metadata in zip(documents, metadatas)
            if page_content
        ]

    def get_documents_for_source(self, vectorstore: Chroma, source_name: str) -> list[Document]:
        """Load all indexed chunks for a single source file, ordered."""
        result = vectorstore.get(
            where={"source": source_name}, include=["documents", "metadatas"]
        )
        documents = result.get("documents", []) or []
        metadatas = result.get("metadatas", []) or []
        loaded = [
            Document(page_content=page_content, metadata=metadata or {})
            for page_content, metadata in zip(documents, metadatas)
            if page_content
        ]
        return sort_by_document_order(loaded)

    def retrieve_for_summary(
        self, vectorstore: Chroma, file_name: str, queries: list[str]
    ) -> list[Document]:
        """Run summary-focused MMR retrieval scoped to one source file."""
        retrieved_documents: list[Document] = []
        for query in queries:
            try:
                results = vectorstore.max_marginal_relevance_search(
                    query=query,
                    k=self.config.summary_query_top_k,
                    fetch_k=self.config.summary_query_fetch_k,
                    lambda_mult=self.config.mmr_lambda,
                    filter={"source": file_name},
                )
            except Exception as error:
                self.logger.warning(
                    "Summary retrieval failed for '%s'. Error: %s", file_name, error
                )
                continue
            retrieved_documents.extend(results)
        return retrieved_documents

    def load_chunk_by_index(
        self, vectorstore: Chroma, source_name: str, chunk_index: int
    ) -> Document | None:
        """Load a specific chunk by metadata from Chroma."""
        result = vectorstore.get(
            where={"$and": [{"source": source_name}, {"chunk_index": chunk_index}]},
            include=["documents", "metadatas"],
        )
        documents = result.get("documents", []) or []
        metadatas = result.get("metadatas", []) or []
        if not documents or not metadatas:
            return None
        return Document(page_content=documents[0], metadata=metadatas[0] or {})

    # ------------------------------------------------------------------
    # BM25 cache management
    # ------------------------------------------------------------------
    def _get_bm25_entry(self, vectorstore: Chroma) -> _BM25CacheEntry | None:
        cache_key = self._collection_cache_key(vectorstore)
        cached = self._bm25_cache.get(cache_key)
        if cached is not None:
            return cached

        indexed_documents = self.get_all_indexed_documents(vectorstore)
        if not indexed_documents:
            return None

        tokenized_corpus = [self._tokenize(document.page_content) for document in indexed_documents]
        entry = _BM25CacheEntry(
            cache_key=cache_key,
            documents=indexed_documents,
            bm25=BM25Okapi(tokenized_corpus),
        )
        self._bm25_cache[cache_key] = entry
        return entry

    @staticmethod
    def _collection_cache_key(vectorstore: Chroma) -> str:
        """Use the collection name when available; fall back to object identity.

        ``Chroma._collection_name`` is the public name passed at construction.
        We avoid `id(vectorstore)` because Streamlit can recreate the wrapper
        across reruns, defeating the cache.
        """
        name = getattr(vectorstore, "_collection_name", None) or getattr(
            vectorstore, "collection_name", None
        )
        if isinstance(name, str) and name:
            return f"collection:{name}"
        return f"vectorstore:{id(vectorstore)}"

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Normalize text into simple alphanumeric tokens for BM25."""
        return re.findall(r"\b\w+\b", text.lower())

    @staticmethod
    def _tag_method(document: Document, method: str) -> Document:
        """Return a copy of the document with `retrieval_method` set."""
        metadata = dict(document.metadata)
        metadata["retrieval_method"] = method
        return Document(page_content=document.page_content, metadata=metadata)


def deduplicate_documents(documents: list[Document]) -> list[Document]:
    """Remove duplicate chunks identified by (source, chunk_index)."""
    seen: set[tuple[str | None, int | None]] = set()
    unique_documents: list[Document] = []
    for document in documents:
        key = (document.metadata.get("source"), document.metadata.get("chunk_index"))
        if key in seen:
            continue
        seen.add(key)
        unique_documents.append(document)
    return unique_documents


def sort_by_document_order(documents: list[Document]) -> list[Document]:
    """Sort chunks by source, page, and chunk index for natural reading order."""
    return sorted(
        documents,
        key=lambda document: (
            str(document.metadata.get("source", "")),
            document.metadata.get("page", 10**9),
            document.metadata.get("chunk_index", 10**9),
        ),
    )
