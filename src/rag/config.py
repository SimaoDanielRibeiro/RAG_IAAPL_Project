"""Configuration values used by the RAG pipeline."""

from __future__ import annotations

from dataclasses import dataclass


FALLBACK_ANSWER = "I could not find that information in the uploaded document."
SUMMARY_FALLBACK = "I could not find enough information in the uploaded document to create a summary."


@dataclass(frozen=True)
class RAGConfig:
    """Centralized knobs for indexing, retrieval, reranking, and answer generation.

    All numeric values are intentionally grouped here so they can be tuned in
    one place. The dataclass is frozen because instances are shared between
    components and must not be mutated mid-flight.
    """

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 100
    chunk_separators: tuple[str, ...] = ("\n\n", "\n", ". ", " ")

    # Vector retrieval
    vector_top_k: int = 8
    exhaustive_top_k: int = 12
    vector_fetch_k_minimum: int = 20
    vector_fetch_multiplier: int = 3
    mmr_lambda: float = 0.7

    # Final selection
    standard_final_chunks: int = 6
    exhaustive_final_chunks: int = 10
    summary_fallback_chunks: int = 5

    # Per-source summarization
    summary_query_top_k: int = 4
    summary_query_fetch_k: int = 12

    # Query expansion
    query_count: int = 3
    max_query_length: int = 220

    # Evidence quality gates (apply only when reranker is in absolute scoring mode)
    rerank_keep_threshold: int = 6
    weak_evidence_average_threshold: float = 6.5
    minimum_supporting_chunks: int = 2

    # Confidence labels
    confidence_high_cutoff: float = 8.0
    confidence_medium_cutoff: float = 6.0

    # Index versioning — bump when stored chunk shape changes
    index_version: str = "hybrid-rag-v3"
