"""Thin orchestration layer for the document RAG pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, AsyncIterator

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import ChatOllama, OllamaEmbeddings

from src.rag.chunking import DocumentChunker
from src.rag.config import FALLBACK_ANSWER, RAGConfig
from src.rag.file_storage import FileStorage
from src.rag.formatting import (
    average_rerank_score,
    build_context,
    confidence_label,
    extract_page_numbers,
    extract_source_names,
    format_citations,
    has_weak_evidence,
)
from src.rag.generation import AnswerGenerator
from src.rag.querying import QueryProcessor
from src.rag.reranking import DocumentReranker
from src.rag.retrieval import HybridRetriever, deduplicate_documents
from src.rag.vector_store import VectorStoreManager
from src.utils import ensure_directory


class DocumentRAGPipeline:
    """Public RAG pipeline API consumed by the FastAPI backend.

    The orchestrator stays intentionally thin: specialized components handle
    storage, chunking, vector-store reuse, retrieval, reranking, and
    generation. This class only wires them together and shapes the response
    payload returned to the API layer.

    Public methods (stable):
    - `save_uploaded_documents(files)`
    - `index_documents(document_paths, content_hash)`
    - `answer_question(vectorstore, question, ...)`
    - `summarize_documents(vectorstore, file_names)`
    """

    def __init__(
        self,
        data_dir: str | Path = "data",
        persist_dir: str | Path = "chroma_db",
        chat_model: str = "qwen2.5:7b-instruct",
        embedding_model: str = "nomic-embed-text",
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        logger: logging.Logger | None = None,
        config: RAGConfig | None = None,
    ) -> None:
        self.config = config or RAGConfig()
        self.data_dir = ensure_directory(data_dir)
        self.persist_dir = ensure_directory(persist_dir)
        self.logger = logger or logging.getLogger("pdf_rag_app")
        self.manifest_path = self.data_dir / "index_manifest.json"

        self.chat_model_name = chat_model
        self.embedding_model_name = embedding_model
        self.reranker_model_name = reranker_model

        self.chat_model = ChatOllama(model=self.chat_model_name, temperature=0)
        self.embeddings = OllamaEmbeddings(model=self.embedding_model_name)

        self.file_storage = FileStorage(self.data_dir)
        self.chunker = DocumentChunker(self.config)
        self.vectorstores = VectorStoreManager(
            persist_dir=self.persist_dir,
            manifest_path=self.manifest_path,
            embeddings=self.embeddings,
            embedding_model_name=self.embedding_model_name,
            chat_model_name=self.chat_model_name,
            reranker_model_name=self.reranker_model_name,
            config=self.config,
            logger=self.logger,
        )
        self.queries = QueryProcessor(self.chat_model, self.config, self.logger)
        self.retriever = HybridRetriever(self.config, self.logger)
        self.reranker = DocumentReranker(
            self.chat_model,
            self.reranker_model_name,
            self.config,
            self.logger,
        )
        self.generator = AnswerGenerator(self.chat_model)

    # ------------------------------------------------------------------
    # File persistence
    # ------------------------------------------------------------------
    def save_uploaded_document(self, file_name: str, file_bytes: bytes) -> Path:
        """Save one uploaded document to disk with path traversal protection."""
        destination = self.file_storage.save_one(file_name, file_bytes)
        self.logger.info("Saved uploaded document to %s", destination)
        return destination

    def save_uploaded_documents(self, files: list[tuple[str, bytes]]) -> list[Path]:
        """Save multiple uploaded documents to disk."""
        return self.file_storage.save_many(files)

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------
    def index_documents(
        self, document_paths: list[str | Path], content_hash: str
    ) -> Chroma:
        """Create or reuse a persistent Chroma collection for these documents."""
        normalized_paths = [Path(document_path) for document_path in document_paths]
        if not normalized_paths:
            raise ValueError("At least one document is required for indexing.")

        collection_seed = (
            normalized_paths[0].name if len(normalized_paths) == 1 else "multi-document-set"
        )
        collection_name = self.vectorstores.resolve_collection_name(collection_seed, content_hash)
        vectorstore = self.vectorstores.open_collection(collection_name)
        if self.vectorstores.collection_has_documents(vectorstore):
            self.logger.info("Reusing existing Chroma collection '%s'", collection_name)
            return vectorstore

        chunks_by_path = {
            document_path: self.chunker.prepare_for_indexing(document_path)
            for document_path in normalized_paths
        }
        return self.vectorstores.create_or_reuse(
            normalized_paths, content_hash, chunks_by_path
        )

    # ------------------------------------------------------------------
    # Question answering
    # ------------------------------------------------------------------
    def answer_question(
        self,
        vectorstore: Chroma,
        question: str,
        top_k: int | None = None,
        chat_history: list[dict[str, str]] | None = None,
        answer_mode: str = "standard",
        source_filter: str | None = None,
        source_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Answer a user question (non-streaming).

        Equivalent to `prepare_answer` followed by `generator.answer` so that
        the streaming and non-streaming paths share the retrieval phase.
        """
        prep = self.prepare_answer(
            vectorstore=vectorstore,
            question=question,
            top_k=top_k,
            chat_history=chat_history,
            answer_mode=answer_mode,
            source_filter=source_filter,
            source_names=source_names,
        )
        if prep.get("fallback"):
            payload = {k: v for k, v in prep.items() if k != "fallback"}
            payload["answer"] = FALLBACK_ANSWER
            return payload

        try:
            answer = self.generator.answer(
                prep["context"], prep["retrieval_question"], answer_mode
            )
        except Exception as error:
            self.logger.exception("Answer generation failed")
            raise RuntimeError(
                f"Could not generate an answer with the chat model: {error}"
            ) from error

        payload = {k: v for k, v in prep.items() if k != "fallback"}
        payload["answer"] = answer
        return payload

    def prepare_answer(
        self,
        vectorstore: Chroma,
        question: str,
        top_k: int | None = None,
        chat_history: list[dict[str, str]] | None = None,
        answer_mode: str = "standard",
        source_filter: str | None = None,
        source_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run retrieval + reranking and return all metadata (no answer yet).

        Adds a `fallback: bool` flag; when True, the caller should emit
        `FALLBACK_ANSWER` instead of invoking the generator.
        """
        retrieval_top_k = top_k if top_k is not None else self.config.vector_top_k
        standalone_question = self.queries.rewrite_with_history(question, chat_history or [])

        retrieval_result = self._run_retrieval_pipeline(
            vectorstore=vectorstore,
            standalone_question=standalone_question,
            answer_mode=answer_mode,
            top_k=retrieval_top_k,
            source_filter=source_filter,
            source_names=source_names or [],
        )
        generated_queries = retrieval_result["generated_queries"]
        selected_docs = retrieval_result["selected_documents"]
        context_docs = retrieval_result["final_documents"]
        context = build_context(context_docs)
        average_score = average_rerank_score(selected_docs)

        if not context.strip() or has_weak_evidence(selected_docs, average_score, self.config):
            payload = self._build_fallback_response(
                generated_queries, standalone_question, answer_mode
            )
            payload.pop("answer", None)
            payload["context"] = ""
            payload["fallback"] = True
            return payload

        return {
            "documents": selected_docs,
            "context": context,
            "confidence": confidence_label(average_score, self.config),
            "pages": extract_page_numbers(selected_docs),
            "sources": extract_source_names(selected_docs),
            "chunks_used": len(selected_docs),
            "average_score": average_score,
            "queries": generated_queries,
            "citations": format_citations(selected_docs),
            "retrieval_question": standalone_question,
            "answer_mode": answer_mode,
            "fallback": False,
        }

    async def astream_answer(
        self, context: str, question: str, answer_mode: str
    ) -> AsyncIterator[str]:
        """Stream answer tokens from the chat model. Use after `prepare_answer`."""
        async for token in self.generator.astream(context, question, answer_mode):
            yield token

    # ------------------------------------------------------------------
    # Summarization
    # ------------------------------------------------------------------
    def summarize_documents(
        self, vectorstore: Chroma, file_names: list[str]
    ) -> dict[str, Any]:
        """Create one retrieval-based summary per uploaded document."""
        summaries: list[dict[str, Any]] = []
        for file_name in file_names:
            source_documents = self.retriever.get_documents_for_source(vectorstore, file_name)
            summaries.append(self._summarize_single_source(vectorstore, file_name, source_documents))
        return {"summaries": summaries}

    def generate_search_queries(self, question: str) -> list[str]:
        """Backward-compatible wrapper for the query expansion step."""
        return self.queries.generate_search_queries(question)

    # ------------------------------------------------------------------
    # Internal orchestration
    # ------------------------------------------------------------------
    def _run_retrieval_pipeline(
        self,
        vectorstore: Chroma,
        standalone_question: str,
        answer_mode: str,
        top_k: int,
        source_filter: str | None = None,
        source_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run query expansion, hybrid retrieval, reranking, and neighbor expansion.

        Order is: retrieve → rerank → select → expand_neighbors. Neighbor
        expansion runs AFTER selection so the reranker scores only what was
        actually retrieved (un-diluted by adjacent-but-off-topic chunks). The
        survivors then get neighbor context for the LLM prompt.

        Two distinct document sets are returned:
        - `selected_documents`: rerank survivors (no neighbors). Used for
          evidence checks, citations, sources, pages.
        - `final_documents`: selected + their neighbors. Used to build the
          LLM context so the model sees fuller passages around each hit.
        """
        retrieval_top_k = (
            self.config.exhaustive_top_k if answer_mode == "exhaustive" else top_k
        )
        generated_queries = self.queries.generate_search_queries(standalone_question)
        use_diverse = not source_filter and bool(source_names)
        if use_diverse:
            retrieved = self.retriever.retrieve_diverse(
                vectorstore, generated_queries, top_k=retrieval_top_k, source_names=source_names
            )
        else:
            retrieved = self.retriever.retrieve(
                vectorstore, generated_queries, top_k=retrieval_top_k, source_filter=source_filter
            )
        unique = deduplicate_documents(retrieved)
        reranked = self.reranker.rerank(
            standalone_question, unique, answer_mode=answer_mode
        )
        selected = self.reranker.select_final_documents(reranked, answer_mode=answer_mode)
        expanded = self.retriever.expand_neighbor_chunks(vectorstore, selected)

        return {
            "generated_queries": generated_queries,
            "retrieved_documents": retrieved,
            "unique_documents": unique,
            "reranked_documents": reranked,
            "selected_documents": selected,
            "expanded_documents": expanded,
            "final_documents": expanded,
        }

    def _summarize_single_source(
        self,
        vectorstore: Chroma,
        file_name: str,
        documents: list[Document],
    ) -> dict[str, Any]:
        """Build a summary entry for one source file."""
        summary_documents = self._retrieve_summary_documents_for_source(
            vectorstore, file_name, documents
        )
        context = build_context(summary_documents)
        try:
            summary = self.generator.summarize(context)
        except Exception as error:
            self.logger.warning(
                "Summary generation failed for '%s'. Error: %s", file_name, error
            )
            from src.rag.config import SUMMARY_FALLBACK

            summary = SUMMARY_FALLBACK

        return {
            "file_name": file_name,
            "summary": summary,
            "documents": summary_documents,
            "pages": extract_page_numbers(summary_documents),
        }

    def _retrieve_summary_documents_for_source(
        self,
        vectorstore: Chroma,
        file_name: str,
        fallback_documents: list[Document],
    ) -> list[Document]:
        """Retrieve the most summary-worthy chunks for one source file."""
        summary_queries = [
            f"Summarize the main ideas, findings, and important sections in {file_name}.",
            f"What are the most important points, sections, and conclusions in {file_name}?",
        ]
        retrieved = self.retriever.retrieve_for_summary(vectorstore, file_name, summary_queries)
        deduplicated = deduplicate_documents(retrieved)
        if not deduplicated:
            deduplicated = fallback_documents[: self.config.standard_final_chunks]
        if not deduplicated:
            return []

        ranked = self.reranker.rerank(
            f"Summarize the most important parts of {file_name}.", deduplicated
        )
        selected = self.reranker.select_final_documents(ranked, answer_mode="standard")
        return selected or deduplicated[: self.config.summary_fallback_chunks]

    def _build_fallback_response(
        self,
        generated_queries: list[str],
        standalone_question: str,
        answer_mode: str,
    ) -> dict[str, Any]:
        """Return the standard payload when no usable evidence is retrieved."""
        return {
            "answer": FALLBACK_ANSWER,
            "documents": [],
            "context": "",
            "confidence": "Low",
            "pages": [],
            "chunks_used": 0,
            "average_score": None,
            "queries": generated_queries,
            "sources": [],
            "citations": [],
            "retrieval_question": standalone_question,
            "answer_mode": answer_mode,
        }
