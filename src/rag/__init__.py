"""Modular RAG package for the document Q&A app.

Public API:
    DocumentRAGPipeline — orchestrator used by the Streamlit UI.
    RAGConfig            — frozen dataclass of all tuning knobs.
"""

from src.rag.config import RAGConfig
from src.rag.pipeline import DocumentRAGPipeline

__all__ = ["DocumentRAGPipeline", "RAGConfig"]
