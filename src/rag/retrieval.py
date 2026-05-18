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
    so it survives backend hot reloads and pipeline re-instantiations.
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
        """Combine semantic MMR retrieval with BM25 keyword retrieval via RRF.

        Each query produces one ranked vector list and one ranked keyword list.
        All ranked lists are fused with Reciprocal Rank Fusion, which rewards
        chunks that surface near the top across multiple lists (especially
        across both retrieval methods). The fused, deduplicated pool is then
        passed to neighbor expansion and the reranker downstream.
        """
        vector_lists = self._retrieve_vector_per_query(
            vectorstore, queries, top_k=top_k, source_filter=source_filter
        )
        keyword_lists = self._retrieve_keyword_per_query(
            vectorstore, queries, top_k=top_k, source_filter=source_filter
        )
        return self._fuse_rrf(vector_lists, keyword_lists, top_k=top_k)

    def retrieve_diverse(
        self,
        vectorstore: Chroma,
        queries: list[str],
        top_k: int,
        source_names: list[str],
    ) -> list[Document]:
        """Per-source RRF-fused retrieval, then merged across sources.

        Retrieves candidates from each source independently so no single large
        document crowds out smaller ones, and fuses each source's vector and
        keyword lists with RRF before merging. The caller deduplicates and
        reranks the merged pool globally.
        """
        if not source_names:
            return self.retrieve(vectorstore, queries, top_k=top_k)
        per_source_k = max(3, (top_k // len(source_names)) + 1)
        all_docs: list[Document] = []
        for source in source_names:
            vector_lists = self._retrieve_vector_per_query(
                vectorstore, queries, top_k=per_source_k, source_filter=source
            )
            keyword_lists = self._retrieve_keyword_per_query(
                vectorstore, queries, top_k=per_source_k, source_filter=source
            )
            fused = self._fuse_rrf(vector_lists, keyword_lists, top_k=per_source_k)
            all_docs.extend(fused)
        return all_docs

    def retrieve_vector(
        self,
        vectorstore: Chroma,
        queries: list[str],
        top_k: int,
        source_filter: str | None = None,
    ) -> list[Document]:
        """Run MMR vector retrieval for each query variant (flattened)."""
        per_query = self._retrieve_vector_per_query(
            vectorstore, queries, top_k=top_k, source_filter=source_filter
        )
        return [document for ranked in per_query for document in ranked]

    def retrieve_keyword(
        self,
        vectorstore: Chroma,
        queries: list[str],
        top_k: int,
        source_filter: str | None = None,
    ) -> list[Document]:
        """Run BM25 keyword retrieval for each query variant (flattened)."""
        per_query = self._retrieve_keyword_per_query(
            vectorstore, queries, top_k=top_k, source_filter=source_filter
        )
        return [document for ranked in per_query for document in ranked]

    # ------------------------------------------------------------------
    # Per-query ranked retrieval (used by RRF fusion)
    # ------------------------------------------------------------------
    def _retrieve_vector_per_query(
        self,
        vectorstore: Chroma,
        queries: list[str],
        top_k: int,
        source_filter: str | None = None,
    ) -> list[list[Document]]:
        """Return one MMR-ranked list per query (preserves rank order)."""
        fetch_k = max(
            top_k * self.config.vector_fetch_multiplier,
            self.config.vector_fetch_k_minimum,
        )
        chroma_filter = {"source": source_filter} if source_filter else None
        ranked_lists: list[list[Document]] = []
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
                ranked_lists.append([])
                continue
            ranked_lists.append([self._tag_method(document, "vector") for document in results])
        return ranked_lists

    def _retrieve_keyword_per_query(
        self,
        vectorstore: Chroma,
        queries: list[str],
        top_k: int,
        source_filter: str | None = None,
    ) -> list[list[Document]]:
        """Return one BM25-ranked list per query (preserves rank order)."""
        if BM25Okapi is None:
            self.logger.info(
                "rank-bm25 is not installed; skipping keyword retrieval. "
                "Install it to enable hybrid search."
            )
            return [[] for _ in queries]

        entry = self._get_bm25_entry(vectorstore)
        if entry is None:
            return [[] for _ in queries]

        # When filtering by source, build an on-the-fly subset index.
        if source_filter:
            docs = [d for d in entry.documents if d.metadata.get("source") == source_filter]
            if not docs:
                return [[] for _ in queries]
            tokenized_corpus = [self._tokenize(d.page_content) for d in docs]
            bm25 = BM25Okapi(tokenized_corpus)
        else:
            docs = entry.documents
            bm25 = entry.bm25

        ranked_lists: list[list[Document]] = []
        for query in queries:
            query_tokens = self._tokenize(query)
            if not query_tokens:
                ranked_lists.append([])
                continue

            scores = bm25.get_scores(query_tokens)
            if not len(scores):
                ranked_lists.append([])
                continue

            ranked_indexes = sorted(
                range(len(scores)), key=lambda index: scores[index], reverse=True
            )[:top_k]

            ranked: list[Document] = []
            for index in ranked_indexes:
                if scores[index] <= 0:
                    continue
                document = docs[index]
                tagged = self._tag_method(document, "keyword")
                tagged.metadata["bm25_score"] = round(float(scores[index]), 4)
                ranked.append(tagged)
            ranked_lists.append(ranked)
        return ranked_lists

    # ------------------------------------------------------------------
    # Reciprocal Rank Fusion
    # ------------------------------------------------------------------
    def _fuse_rrf(
        self,
        vector_lists: list[list[Document]],
        keyword_lists: list[list[Document]],
        top_k: int,
    ) -> list[Document]:
        """Fuse ranked lists with Reciprocal Rank Fusion.

        For each ranked list, every document at rank `r` (1-indexed) contributes
        `1 / (k + r)` to its fused score. Documents appearing across multiple
        lists — and especially across both retrieval methods — accumulate the
        highest scores, surfacing chunks that are robust under both semantic
        and lexical signals.

        Tagging:
        - retrieval_method = "hybrid" when a doc was returned by both vector
          and keyword retrievers, otherwise its single method's tag.
        - rrf_score is stored on metadata for downstream inspection.

        The returned pool is capped at `top_k * config.rrf_pool_multiplier`
        so the reranker still sees a reasonably sized candidate set.
        """
        rrf_k = self.config.rrf_k
        # key -> (best_seen_document, accumulated_score, methods_set, page_priority)
        scores: dict[tuple[Any, Any], float] = {}
        best_doc: dict[tuple[Any, Any], Document] = {}
        methods: dict[tuple[Any, Any], set[str]] = {}

        def _accumulate(ranked_list: list[Document], method: str) -> None:
            for rank, document in enumerate(ranked_list, start=1):
                key = (
                    document.metadata.get("source"),
                    document.metadata.get("chunk_index"),
                )
                scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
                methods.setdefault(key, set()).add(method)
                # Keep the first-seen document instance as the canonical copy.
                best_doc.setdefault(key, document)

        for ranked in vector_lists:
            _accumulate(ranked, "vector")
        for ranked in keyword_lists:
            _accumulate(ranked, "keyword")

        if not scores:
            return []

        ranked_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        pool_size = max(top_k, top_k * self.config.rrf_pool_multiplier)

        fused: list[Document] = []
        for key in ranked_keys[:pool_size]:
            source_doc = best_doc[key]
            method_set = methods[key]
            final_method = "hybrid" if len(method_set) > 1 else next(iter(method_set))
            metadata = dict(source_doc.metadata)
            metadata["retrieval_method"] = final_method
            metadata["rrf_score"] = round(scores[key], 6)
            fused.append(Document(page_content=source_doc.page_content, metadata=metadata))
        return fused

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
        We avoid `id(vectorstore)` because the wrapper can be recreated when
        the backend reloads, which would otherwise defeat the cache.
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
