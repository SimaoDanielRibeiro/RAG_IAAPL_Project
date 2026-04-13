"""Core RAG pipeline for indexing documents and answering questions."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.document_loaders import load_source_documents
from src.prompts import (
    ANSWER_PROMPT_TEMPLATE,
    EXHAUSTIVE_ANSWER_PROMPT_TEMPLATE,
    REWRITE_QUESTION_PROMPT_TEMPLATE,
    RERANK_PROMPT_TEMPLATE,
    SUMMARY_PROMPT_TEMPLATE,
    SYSTEM_PROMPT,
)
from src.utils import ensure_directory, load_json_file, safe_collection_name, save_json_file


class PDFRAGPipeline:
    """Simple document RAG pipeline with Chroma persistence and Ollama models."""

    def __init__(
        self,
        data_dir: str = "data",
        persist_dir: str = "chroma_db",
        chat_model: str = "llama3.2:3b",
        embedding_model: str = "nomic-embed-text",
        logger: logging.Logger | None = None,
    ) -> None:
        self.data_dir = ensure_directory(data_dir)
        self.persist_dir = ensure_directory(persist_dir)
        self.logger = logger or logging.getLogger("pdf_rag_app")
        self.manifest_path = self.data_dir / "index_manifest.json"

        self.chat_model_name = chat_model
        self.embedding_model_name = embedding_model

        self.chat_model = ChatOllama(model=self.chat_model_name, temperature=0)
        self.embeddings = OllamaEmbeddings(model=self.embedding_model_name)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " "],
        )

    def save_uploaded_document(self, file_name: str, file_bytes: bytes) -> Path:
        """Save an uploaded document to disk."""
        destination = self.data_dir / file_name
        destination.write_bytes(file_bytes)
        self.logger.info("Saved uploaded document to %s", destination)
        return destination

    def save_uploaded_documents(self, files: list[tuple[str, bytes]]) -> list[Path]:
        """Save multiple uploaded documents to disk."""
        return [self.save_uploaded_document(file_name, file_bytes) for file_name, file_bytes in files]

    def index_documents(self, document_paths: list[str | Path], content_hash: str) -> Chroma:
        """Create or reuse a persistent Chroma collection for one or more documents."""
        normalized_paths = [Path(document_path) for document_path in document_paths]
        if not normalized_paths:
            raise ValueError("At least one document is required for indexing.")

        collection_seed_name = normalized_paths[0].name if len(normalized_paths) == 1 else "multi-document-set"
        collection_name = self._resolve_collection_name(collection_seed_name, content_hash)
        vectorstore = Chroma(
            collection_name=collection_name,
            persist_directory=str(self.persist_dir),
            embedding_function=self.embeddings,
        )

        existing_count = vectorstore._collection.count()
        if existing_count > 0:
            self.logger.info(
                "Reusing existing Chroma collection '%s' with %s chunks",
                collection_name,
                existing_count,
            )
            return vectorstore

        self.logger.info("Indexing %s document(s) into collection '%s'", len(normalized_paths), collection_name)
        all_documents: list[Document] = []

        for document_path in normalized_paths:
            loaded_documents = load_source_documents(document_path)
            extracted_text = " ".join(
                document.page_content.strip()
                for document in loaded_documents
                if document.page_content.strip()
            )
            if not extracted_text:
                raise ValueError(
                    f"No readable text was extracted from '{document_path.name}'. If it is scanned, OCR may be required before upload."
                )

            chunks = self.text_splitter.split_documents(loaded_documents)
            if not chunks:
                raise ValueError(f"No text chunks could be created from '{document_path.name}'.")

            all_documents.extend(self._add_chunk_metadata(chunks, document_path.name))

        vectorstore.add_documents(all_documents)
        self._save_manifest_entry(
            [document_path.name for document_path in normalized_paths],
            content_hash,
            collection_name,
            len(all_documents),
        )
        self.logger.info("Indexed %s chunks for %s document(s)", len(all_documents), len(normalized_paths))
        return vectorstore

    def answer_question(
        self,
        vectorstore: Chroma,
        question: str,
        top_k: int = 8,
        chat_history: list[dict[str, str]] | None = None,
        answer_mode: str = "standard",
    ) -> dict[str, Any]:
        """Answer a user question using multi-query retrieval over the document context."""
        standalone_question = self._rewrite_question_with_history(question, chat_history or [])
        retrieval_top_k = 12 if answer_mode == "exhaustive" else top_k
        generated_queries = self.generate_search_queries(standalone_question)
        retrieved_docs = self._retrieve_documents(vectorstore, generated_queries, top_k=retrieval_top_k)
        deduplicated_docs = self._deduplicate_documents(retrieved_docs)
        expanded_docs = self._expand_neighbor_chunks(vectorstore, deduplicated_docs)
        reranked_docs = self._rerank_documents(standalone_question, expanded_docs)
        final_docs = self._select_final_documents(reranked_docs, answer_mode=answer_mode)
        context = self._build_context(final_docs)

        average_score = self._average_rerank_score(final_docs)
        if not context.strip() or self._has_weak_evidence(final_docs, average_score):
            fallback = "I could not find that information in the uploaded document."
            return {
                "answer": fallback,
                "documents": [],
                "context": "",
                "confidence": "Low",
                "pages": [],
                "chunks_used": 0,
                "average_score": None,
                "queries": generated_queries,
                "sources": [],
                "retrieval_question": standalone_question,
                "answer_mode": answer_mode,
            }

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                (
                    "human",
                    EXHAUSTIVE_ANSWER_PROMPT_TEMPLATE if answer_mode == "exhaustive" else ANSWER_PROMPT_TEMPLATE,
                ),
            ]
        )
        chain = prompt | self.chat_model | StrOutputParser()
        answer = chain.invoke({"context": context, "question": standalone_question}).strip()

        if not answer:
            answer = "I could not find that information in the uploaded document."

        pages = self._extract_page_numbers(final_docs)
        sources = self._extract_source_names(final_docs)

        return {
            "answer": answer,
            "documents": final_docs,
            "context": context,
            "confidence": self._confidence_label(average_score),
            "pages": pages,
            "sources": sources,
            "chunks_used": len(final_docs),
            "average_score": average_score,
            "queries": generated_queries,
            "citations": self._format_citations(final_docs),
            "retrieval_question": standalone_question,
            "answer_mode": answer_mode,
        }

    def summarize_documents(self, vectorstore: Chroma, file_names: list[str]) -> dict[str, Any]:
        """Create one summary per uploaded document."""
        summaries: list[dict[str, Any]] = []
        for file_name in file_names:
            documents = self._get_documents_for_source(vectorstore, file_name)
            summaries.append(self._summarize_single_source(vectorstore, file_name, documents))
        return {"summaries": summaries}

    def generate_search_queries(self, question: str) -> list[str]:
        """Generate the original question plus two retrieval-focused rewrites."""
        query_prompt = PromptTemplate(
            input_variables=["question"],
            template=(
                "You are helping expand a user question for document retrieval.\n"
                "Generate exactly 2 alternative versions of the user's question.\n"
                "Focus on wording changes that improve recall.\n"
                "Return only the 2 alternative questions, one per line, and do not number them.\n\n"
                "Original question: {question}"
            ),
        )
        chain = query_prompt | self.chat_model | StrOutputParser()
        response = chain.invoke({"question": question}).strip()
        alternatives = [
            self._sanitize_retrieval_question(line.strip("- ").strip(), fallback=question)
            for line in response.splitlines()
            if line.strip()
        ]
        base_question = self._sanitize_retrieval_question(question, fallback=question)
        queries = [base_question]
        for candidate in alternatives:
            if candidate and candidate.lower() not in {query.lower() for query in queries}:
                queries.append(candidate)
            if len(queries) == 3:
                break
        while len(queries) < 3:
            queries.append(base_question)
        return queries

    def _rewrite_question_with_history(self, question: str, chat_history: list[dict[str, str]]) -> str:
        """Rewrite follow-up questions into standalone retrieval questions when needed."""
        if not chat_history:
            return question

        history_text = self._format_chat_history(chat_history)
        if not history_text:
            return question

        rewrite_prompt = PromptTemplate(
            input_variables=["chat_history", "question"],
            template=REWRITE_QUESTION_PROMPT_TEMPLATE,
        )
        chain = rewrite_prompt | self.chat_model | StrOutputParser()
        rewritten_question = chain.invoke(
            {"chat_history": history_text, "question": question}
        ).strip()
        return self._sanitize_retrieval_question(rewritten_question, fallback=question)

    def _format_chat_history(self, chat_history: list[dict[str, str]]) -> str:
        """Format a small recent chat history window for rewrite prompts."""
        lines: list[str] = []
        for message in chat_history[-4:]:
            role = message.get("role")
            content = message.get("content", "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            role_label = "User" if role == "user" else "Assistant"
            lines.append(f"{role_label}: {content}")
        return "\n".join(lines)

    def _sanitize_retrieval_question(self, candidate: str, fallback: str) -> str:
        """Keep retrieval questions short, single-line, and question-like."""
        cleaned = " ".join(candidate.split()).strip()
        fallback_clean = " ".join(fallback.split()).strip()
        if not cleaned:
            return fallback_clean

        if "\n" in candidate:
            cleaned = " ".join(candidate.splitlines()[0].split()).strip()

        for separator in [". ", "\n", " Answer:", " Explanation:", " Because "]:
            if separator in cleaned:
                cleaned = cleaned.split(separator, 1)[0].strip()

        if not cleaned:
            return fallback_clean

        if len(cleaned) > 220:
            cleaned = cleaned[:220].rsplit(" ", 1)[0].strip()

        answer_like_markers = [
            " is ",
            " are ",
            " refers to ",
            " means ",
            " can be defined as ",
        ]
        lowered = cleaned.lower()
        if not cleaned.endswith("?") and any(marker in lowered for marker in answer_like_markers):
            return fallback_clean

        if not cleaned.endswith("?"):
            cleaned = f"{cleaned}?"

        return cleaned

    def _retrieve_documents(self, vectorstore: Chroma, queries: list[str], top_k: int) -> list[Document]:
        """Run MMR retrieval for each query variant and combine the results."""
        retrieved_documents: list[Document] = []
        for query in queries:
            results = vectorstore.max_marginal_relevance_search(
                query=query,
                k=top_k,
                fetch_k=20,
                lambda_mult=0.7,
            )
            retrieved_documents.extend(results)
        return retrieved_documents

    def _get_documents_for_source(self, vectorstore: Chroma, source_name: str) -> list[Document]:
        """Load all indexed chunks for a single source file."""
        result = vectorstore.get(where={"source": source_name}, include=["documents", "metadatas"])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        loaded_documents = [
            Document(page_content=page_content, metadata=metadata)
            for page_content, metadata in zip(documents, metadatas)
        ]
        return sorted(
            loaded_documents,
            key=lambda document: (
                document.metadata.get("page", 10**9),
                document.metadata.get("chunk_index", 10**9),
            ),
        )

    def _add_chunk_metadata(self, chunks: list[Document], source_name: str) -> list[Document]:
        """Attach consistent metadata to each chunk."""
        documents: list[Document] = []
        total_chunks = len(chunks)
        for index, chunk in enumerate(chunks):
            metadata = dict(chunk.metadata)
            metadata["source"] = source_name
            metadata["chunk_index"] = index
            metadata["chunk_size"] = len(chunk.page_content)
            metadata["previous_chunk_index"] = index - 1 if index > 0 else None
            metadata["next_chunk_index"] = index + 1 if index < total_chunks - 1 else None
            metadata["section_title"] = self._detect_section_title(chunk.page_content)
            documents.append(Document(page_content=chunk.page_content, metadata=metadata))
        return documents

    def _deduplicate_documents(self, documents: list[Document]) -> list[Document]:
        """Remove duplicate chunks returned by multi-query retrieval."""
        seen: set[tuple[str | None, int | None]] = set()
        unique_documents: list[Document] = []

        for document in documents:
            key = (document.metadata.get("source"), document.metadata.get("chunk_index"))
            if key in seen:
                continue
            seen.add(key)
            unique_documents.append(document)

        return unique_documents

    def _expand_neighbor_chunks(self, vectorstore: Chroma, documents: list[Document]) -> list[Document]:
        """Include previous and next chunks for retrieved results when available."""
        expanded_documents: list[Document] = list(documents)

        for document in documents:
            source = document.metadata.get("source")
            previous_chunk_index = document.metadata.get("previous_chunk_index")
            next_chunk_index = document.metadata.get("next_chunk_index")

            for chunk_index in (previous_chunk_index, next_chunk_index):
                if source is None or chunk_index is None:
                    continue
                neighbor = self._load_chunk_by_index(vectorstore, source, chunk_index)
                if neighbor is not None:
                    expanded_documents.append(neighbor)

        return self._deduplicate_documents(expanded_documents)

    def _load_chunk_by_index(self, vectorstore: Chroma, source_name: str, chunk_index: int) -> Document | None:
        """Load a specific chunk by metadata from Chroma."""
        result = vectorstore.get(
            where={"$and": [{"source": source_name}, {"chunk_index": chunk_index}]},
            include=["documents", "metadatas"],
        )

        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        if not documents or not metadatas:
            return None

        return Document(page_content=documents[0], metadata=metadatas[0])

    def _rerank_documents(self, question: str, documents: list[Document]) -> list[Document]:
        """Score retrieved chunks and keep scores in metadata."""
        reranked_documents: list[Document] = []

        for document in documents:
            score = self._score_document_relevance(question, document.page_content)
            metadata = dict(document.metadata)
            metadata["rerank_score"] = score
            reranked_documents.append(Document(page_content=document.page_content, metadata=metadata))

        return reranked_documents

    def _score_document_relevance(self, question: str, chunk: str) -> int:
        """Ask the model to produce a simple 1-10 relevance score for a chunk."""
        prompt = RERANK_PROMPT_TEMPLATE.format(question=question, chunk=chunk)
        response = self.chat_model.invoke(prompt)
        content = getattr(response, "content", str(response)).strip()
        match = re.search(r"\b([1-9]|10)\b", content)
        if match:
            return int(match.group(1))
        return 1

    def _select_final_documents(self, documents: list[Document], answer_mode: str = "standard") -> list[Document]:
        """Apply thresholding, keep top chunks, and order them for context building."""
        thresholded = [document for document in documents if document.metadata.get("rerank_score", 0) >= 6]
        if not thresholded:
            return []

        ranked = sorted(
            thresholded,
            key=lambda document: (
                -document.metadata.get("rerank_score", 0),
                document.metadata.get("page", 10**9),
                document.metadata.get("chunk_index", 10**9),
            ),
        )
        max_chunks = 10 if answer_mode == "exhaustive" else 6
        top_documents = ranked[:max_chunks]
        return sorted(
            top_documents,
            key=lambda document: (
                document.metadata.get("page", 10**9),
                document.metadata.get("chunk_index", 10**9),
            ),
        )

    def _has_weak_evidence(self, documents: list[Document], average_score: float | None) -> bool:
        """Reject answers when the retrieval evidence is too weak."""
        if len(documents) < 2:
            return True
        if average_score is None:
            return True
        return average_score < 6.5

    def _build_context(self, documents: list[Document]) -> str:
        """Format retrieved documents into a single context string for the LLM."""
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

    def _summarize_single_source(
        self,
        vectorstore: Chroma,
        file_name: str,
        documents: list[Document],
    ) -> dict[str, Any]:
        """Create a summary for one source file."""
        summary_documents = self._retrieve_summary_documents_for_source(vectorstore, file_name, documents)
        context = self._build_context(summary_documents)
        if not context.strip():
            summary = "I could not find enough information in the uploaded document to create a summary."
        else:
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", SYSTEM_PROMPT),
                    ("human", SUMMARY_PROMPT_TEMPLATE),
                ]
            )
            chain = prompt | self.chat_model | StrOutputParser()
            summary = chain.invoke({"context": context}).strip()

        return {
            "file_name": file_name,
            "summary": summary,
            "documents": summary_documents,
            "pages": self._extract_page_numbers(summary_documents),
        }

    def _retrieve_summary_documents_for_source(
        self,
        vectorstore: Chroma,
        file_name: str,
        fallback_documents: list[Document],
    ) -> list[Document]:
        """Retrieve the most summary-worthy chunks for a single source file."""
        summary_queries = [
            f"Summarize the main ideas, findings, and important sections in {file_name}.",
            f"What are the most important points, sections, and conclusions in {file_name}?",
        ]

        retrieved_documents: list[Document] = []
        for query in summary_queries:
            try:
                results = vectorstore.max_marginal_relevance_search(
                    query=query,
                    k=4,
                    fetch_k=12,
                    lambda_mult=0.7,
                    filter={"source": file_name},
                )
            except Exception:
                results = []
            retrieved_documents.extend(results)

        deduplicated_documents = self._deduplicate_documents(retrieved_documents)
        if not deduplicated_documents:
            deduplicated_documents = fallback_documents[:6]

        ranked_documents = self._rerank_documents(
            f"Summarize the most important parts of {file_name}.",
            deduplicated_documents,
        )
        selected_documents = self._select_final_documents(ranked_documents)
        if not selected_documents:
            selected_documents = deduplicated_documents[:5]
        return selected_documents

    def _detect_section_title(self, chunk_text: str) -> str | None:
        """Heuristically detect a heading-like first line in a chunk."""
        for raw_line in chunk_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if len(line) > 80:
                return None
            if line.isupper():
                return line
            if re.match(r"^\d+(\.\d+)*\s+[A-Z].*", line):
                return line
            if line == line.title() and len(line.split()) <= 10:
                return line
            return None
        return None

    def _extract_page_numbers(self, documents: list[Document]) -> list[int]:
        """Return sorted unique 1-based page numbers used in the final answer."""
        pages = {
            document.metadata["page"] + 1
            for document in documents
            if document.metadata.get("page") is not None
        }
        return sorted(pages)

    def _extract_source_names(self, documents: list[Document]) -> list[str]:
        """Return sorted unique source file names used in the final answer."""
        sources = {
            document.metadata["source"]
            for document in documents
            if document.metadata.get("source")
        }
        return sorted(sources)

    def _format_citations(self, documents: list[Document]) -> list[str]:
        """Build deterministic file and page citations from the final documents."""
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

    def _average_rerank_score(self, documents: list[Document]) -> float | None:
        """Compute the average rerank score of the final chunks."""
        scores = [document.metadata.get("rerank_score") for document in documents]
        valid_scores = [score for score in scores if isinstance(score, (int, float))]
        if not valid_scores:
            return None
        return round(sum(valid_scores) / len(valid_scores), 2)

    def _confidence_label(self, average_score: float | None) -> str:
        """Map the average rerank score to a simple confidence label."""
        if average_score is None:
            return "Low"
        if average_score >= 8:
            return "High"
        if average_score >= 6:
            return "Medium"
        return "Low"

    def _resolve_collection_name(self, file_name: str, content_hash: str) -> str:
        """Reuse the stored collection name for this document set when available."""
        manifest = load_json_file(self.manifest_path)
        entry = manifest.get(content_hash)
        if entry:
            return entry["collection_name"]
        return safe_collection_name(file_name, content_hash)

    def _save_manifest_entry(
        self,
        file_names: list[str],
        content_hash: str,
        collection_name: str,
        chunk_count: int,
    ) -> None:
        """Persist indexing metadata for reuse and debugging."""
        manifest = load_json_file(self.manifest_path)
        manifest[content_hash] = {
            "file_names": file_names,
            "collection_name": collection_name,
            "chunk_count": chunk_count,
            "chat_model": self.chat_model_name,
            "embedding_model": self.embedding_model_name,
        }
        save_json_file(self.manifest_path, manifest)
