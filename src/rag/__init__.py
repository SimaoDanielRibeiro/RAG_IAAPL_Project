"""Modular RAG package for the document Q&A app.

This package implements the full Retrieval-Augmented Generation pipeline
used by the FastAPI backend (`backend/`). The flow is:

    file_storage  ->  pdf_extractor  ->  document_loader
                                              |
                                              v
                       chunking  ->  vector_store (Chroma + embeddings)
                                              |
    user question                              |
         |          query rewriting            |
         v          + expansion                v
    querying.py  ->  retrieval.py  (hybrid: MMR vector + BM25 + RRF fusion)
                                              |
                                              v
                       reranking.py  (CrossEncoder; LLM fallback)
                                              |
                                              v
                       pipeline.py  (selects, expands neighbors,
                                     formats context, generates answer)
                                              |
                                              v
                       generation.py  (LLM call) + formatting.py (citations)

Public API:
    DocumentRAGPipeline — orchestrator used by the FastAPI backend.
    RAGConfig            — frozen dataclass of all tuning knobs.
"""

from src.rag.config import RAGConfig
from src.rag.pipeline import DocumentRAGPipeline

__all__ = ["DocumentRAGPipeline", "RAGConfig"]
