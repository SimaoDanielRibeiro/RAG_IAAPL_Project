"""Document reranking for retrieved chunks."""

from __future__ import annotations

import logging
import math
import re
from typing import Any

from langchain_core.documents import Document
from langchain_ollama import ChatOllama

from src.rag.config import RAGConfig
from src.rag.prompts import RERANK_PROMPT_TEMPLATE
from src.rag.retrieval import sort_by_document_order


class DocumentReranker:
    """Score chunks with a CrossEncoder, falling back to LLM scoring.

    The reranker writes one of two score scales onto each chunk:
    - "absolute" (LLM fallback) — integer 1-10 reflecting absolute relevance.
      Selection applies a keep-threshold and weak-evidence guards downstream.
    - "relative" (CrossEncoder) — integer 1-10 normalized within the batch.
      Selection takes top-N without thresholding, because every batch has at
      least one near-10 by construction.
    """

    def __init__(
        self,
        chat_model: ChatOllama,
        reranker_model_name: str,
        config: RAGConfig,
        logger: logging.Logger,
    ) -> None:
        self.chat_model = chat_model
        self.reranker_model_name = reranker_model_name
        self.config = config
        self.logger = logger
        self._reranker: Any | None = None
        self._load_attempted = False

    def rerank(self, question: str, documents: list[Document]) -> list[Document]:
        """Score retrieved chunks and store scores in metadata."""
        if not documents:
            return []

        reranker = self._get_reranker()
        if reranker is None:
            return self._rerank_with_llm(question, documents)

        try:
            pairs = [(question, document.page_content) for document in documents]
            raw_scores = [float(score) for score in reranker.predict(pairs)]
        except Exception as error:
            self.logger.warning(
                "Dedicated reranker failed; falling back to LLM scoring. Error: %s", error
            )
            return self._rerank_with_llm(question, documents)

        normalized_scores = self._normalize_scores(raw_scores)
        reranked_documents: list[Document] = []
        for document, raw_score, normalized_score in zip(documents, raw_scores, normalized_scores):
            metadata = dict(document.metadata)
            metadata["rerank_score"] = normalized_score
            metadata["rerank_raw_score"] = round(float(raw_score), 4)
            metadata["rerank_score_scale"] = "relative"
            metadata["reranker_model"] = self.reranker_model_name
            reranked_documents.append(
                Document(page_content=document.page_content, metadata=metadata)
            )
        return reranked_documents

    def select_final_documents(
        self, documents: list[Document], answer_mode: str = "standard"
    ) -> list[Document]:
        """Keep the strongest chunks and order them for context building.

        For absolute-scale (LLM) scores, drop chunks below `rerank_keep_threshold`.
        For relative-scale (CrossEncoder) scores, just keep top-N by score.
        """
        if not documents:
            return []

        score_scale = self._dominant_score_scale(documents)
        candidates = (
            [
                document
                for document in documents
                if document.metadata.get("rerank_score", 0) >= self.config.rerank_keep_threshold
            ]
            if score_scale == "absolute"
            else list(documents)
        )
        if not candidates:
            return []

        ranked = sorted(
            candidates,
            key=lambda document: (
                -document.metadata.get("rerank_score", 0),
                document.metadata.get("page", 10**9),
                document.metadata.get("chunk_index", 10**9),
            ),
        )
        max_chunks = (
            self.config.exhaustive_final_chunks
            if answer_mode == "exhaustive"
            else self.config.standard_final_chunks
        )
        return sort_by_document_order(ranked[:max_chunks])

    # ------------------------------------------------------------------
    # CrossEncoder lazy-loading
    # ------------------------------------------------------------------
    def _get_reranker(self) -> Any | None:
        """Lazy-load the CrossEncoder so app startup does not freeze."""
        if self._load_attempted:
            return self._reranker

        self._load_attempted = True
        try:
            from sentence_transformers import CrossEncoder
        except ImportError:
            self.logger.info(
                "sentence-transformers is not installed; using LLM reranking. "
                "Install it for faster, better-quality reranking."
            )
            return None

        try:
            self._reranker = CrossEncoder(self.reranker_model_name)
        except Exception as error:
            self.logger.warning(
                "Could not load reranker '%s'. Falling back to LLM reranking. Error: %s",
                self.reranker_model_name,
                error,
            )
            self._reranker = None
        return self._reranker

    # ------------------------------------------------------------------
    # LLM fallback path
    # ------------------------------------------------------------------
    def _rerank_with_llm(self, question: str, documents: list[Document]) -> list[Document]:
        """Score each chunk by asking the chat model for a 1-10 relevance value."""
        reranked_documents: list[Document] = []
        for document in documents:
            score = self._score_with_llm(question, document.page_content)
            metadata = dict(document.metadata)
            metadata["rerank_score"] = score
            metadata["rerank_score_scale"] = "absolute"
            metadata["reranker_model"] = "llm-fallback"
            reranked_documents.append(
                Document(page_content=document.page_content, metadata=metadata)
            )
        return reranked_documents

    def _score_with_llm(self, question: str, chunk: str) -> int:
        """Ask the model to produce a 1-10 relevance score for a chunk."""
        prompt = RERANK_PROMPT_TEMPLATE.format(question=question, chunk=chunk)
        try:
            response = self.chat_model.invoke(prompt)
        except Exception as error:
            self.logger.warning("LLM reranking failed for one chunk. Error: %s", error)
            return 1

        content = getattr(response, "content", str(response)).strip()
        match = re.search(r"\b([1-9]|10)\b", content)
        return int(match.group(1)) if match else 1

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_scores(raw_scores: list[float]) -> list[int]:
        """Convert CrossEncoder logits into a 1-10 integer ranking scale."""
        if not raw_scores:
            return []

        min_score = min(raw_scores)
        max_score = max(raw_scores)
        if math.isclose(min_score, max_score):
            return [6 for _ in raw_scores]

        normalized: list[int] = []
        spread = max_score - min_score
        for raw_score in raw_scores:
            scaled = 1 + 9 * ((raw_score - min_score) / spread)
            normalized.append(max(1, min(10, round(scaled))))
        return normalized

    @staticmethod
    def _dominant_score_scale(documents: list[Document]) -> str:
        """Return the scoring scale most chunks were rated on."""
        scales = [
            document.metadata.get("rerank_score_scale", "absolute")
            for document in documents
        ]
        if not scales:
            return "absolute"
        return "relative" if scales.count("relative") > len(scales) // 2 else "absolute"
