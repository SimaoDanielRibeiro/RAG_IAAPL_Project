"""Formatting helpers for RAG context, citations, evidence, and confidence labels."""

from __future__ import annotations

from langchain_core.documents import Document

from src.rag.config import RAGConfig


def build_context(documents: list[Document]) -> str:
    """Format retrieved documents into a single context string for the LLM.

    Each section header carries source, page (1-based), chunk index, and
    optional section title so the model can cite faithfully.
    """
    sections: list[str] = []
    for document in documents:
        page = document.metadata.get("page")
        chunk_index = document.metadata.get("chunk_index")
        section_title = document.metadata.get("section_title")
        source_name = document.metadata.get("source", "Unknown file")

        header = f"Page {page + 1}" if page is not None else "Page unknown"
        header = f"{source_name} | {header}"
        if chunk_index is not None:
            header = f"{header} | Chunk {chunk_index}"
        if section_title:
            header = f"{header} | Section: {section_title}"

        sections.append(f"{header}:\n{document.page_content.strip()}")
    return "\n\n".join(sections)


def extract_page_numbers(documents: list[Document]) -> list[int]:
    """Return sorted unique 1-based page numbers used in the final answer."""
    pages = {
        document.metadata["page"] + 1
        for document in documents
        if document.metadata.get("page") is not None
    }
    return sorted(pages)


def extract_source_names(documents: list[Document]) -> list[str]:
    """Return sorted unique source file names used in the final answer."""
    sources = {
        document.metadata["source"]
        for document in documents
        if document.metadata.get("source")
    }
    return sorted(sources)


def format_citations(documents: list[Document]) -> list[str]:
    """Build deterministic file-and-page citations from final documents.

    Output is one citation per source file: ``"my_file.pdf (Pages 3, 5, 9)"``.
    """
    citation_map: dict[str, set[int]] = {}
    for document in documents:
        source_name = document.metadata.get("source", "Unknown file")
        page_number = document.metadata.get("page")
        citation_map.setdefault(source_name, set())
        if page_number is not None:
            citation_map[source_name].add(page_number + 1)

    citations: list[str] = []
    for source_name in sorted(citation_map):
        pages = sorted(citation_map[source_name])
        if pages:
            pages_label = ", ".join(str(page) for page in pages)
            citations.append(f"{source_name} (Pages {pages_label})")
        else:
            citations.append(source_name)
    return citations


def average_rerank_score(documents: list[Document]) -> float | None:
    """Compute the average rerank score of final chunks, or None when missing."""
    scores = [document.metadata.get("rerank_score") for document in documents]
    valid_scores = [score for score in scores if isinstance(score, (int, float))]
    if not valid_scores:
        return None
    return round(sum(valid_scores) / len(valid_scores), 2)


def confidence_label(average_score: float | None, config: RAGConfig) -> str:
    """Map the average rerank score to a simple confidence label."""
    if average_score is None:
        return "Low"
    if average_score >= config.confidence_high_cutoff:
        return "High"
    if average_score >= config.confidence_medium_cutoff:
        return "Medium"
    return "Low"


def has_weak_evidence(
    documents: list[Document],
    average_score: float | None,
    config: RAGConfig,
) -> bool:
    """Return True when retrieved evidence is too weak to support an answer.

    Evidence is "weak" when:
    - Fewer than `minimum_supporting_chunks` chunks survived selection, OR
    - Scores were produced on the absolute (LLM) scale and the average is
      below `weak_evidence_average_threshold`.

    For relative-scale (CrossEncoder) scores the only check is the chunk
    count, because a CrossEncoder always produces a top score regardless of
    absolute relevance.
    """
    if len(documents) < config.minimum_supporting_chunks:
        return True

    score_scale = _dominant_score_scale(documents)
    if score_scale == "absolute":
        if average_score is None:
            return True
        return average_score < config.weak_evidence_average_threshold

    return False


def _dominant_score_scale(documents: list[Document]) -> str:
    """Return whichever score scale most chunks were rated on ("absolute" by default)."""
    scales = [
        document.metadata.get("rerank_score_scale", "absolute")
        for document in documents
    ]
    if not scales:
        return "absolute"
    return "relative" if scales.count("relative") > len(scales) // 2 else "absolute"
