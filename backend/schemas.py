"""Pydantic request/response schemas for the FastAPI backend.

These models define the contract between the backend and the Next.js
frontend. Field names match the JSON the frontend expects.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Backend health and model status payload."""

    status: str
    documents_count: int
    chat_model: str
    embedding_model: str


class DocumentInfo(BaseModel):
    """One indexed document as seen by the frontend (id, name, size)."""

    id: str
    name: str
    size_bytes: int


class UploadResponse(BaseModel):
    """Response after one or more files have been uploaded and indexed."""

    documents: list[DocumentInfo]
    message: str


class ChatRequest(BaseModel):
    """Incoming question for the /chat and /chat/stream endpoints.

    Fields:
        question     — the raw user question.
        answer_mode  — "standard" (concise) or "exhaustive" (full extraction).
        chat_history — recent conversation turns, used by the rewriter
                       to make follow-up questions self-contained.
        document_ids — optional subset of active documents to search in;
                       empty list means "all active documents".
    """

    question: str
    answer_mode: str = "standard"
    chat_history: list[dict] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)


class ChunkInfo(BaseModel):
    """One retrieved chunk surfaced to the Evidence panel in the UI."""

    source: str
    page: Optional[int] = None
    score: Optional[float] = None
    score_scale: Optional[str] = None
    snippet: str
    document_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Full answer payload returned by the non-streaming /chat endpoint.

    Mirrors the structure of the metadata frame emitted by /chat/stream
    so both endpoints look the same to the frontend.
    """

    answer: str
    confidence: str
    sources: list[str]
    pages: list[int]
    citations: list[str]
    chunks_used: int
    average_score: Optional[float] = None
    queries: list[str]
    retrieval_question: str
    documents: list[ChunkInfo]
    context_documents: list[ChunkInfo] = Field(default_factory=list)
    answer_mode: str
    source_distribution: dict[str, int] = Field(default_factory=dict)
    document_ids: list[str] = Field(default_factory=list)


class SummaryRequest(BaseModel):
    """Optional document scope for the /summary endpoint."""

    document_ids: list[str] = Field(default_factory=list)


class SummaryEntry(BaseModel):
    """Per-file summary produced by the /summary endpoint."""

    file_name: str
    summary: str
    pages: list[int]


class SummaryResponse(BaseModel):
    """Aggregate of per-file summaries for the active document set."""

    summaries: list[SummaryEntry]
