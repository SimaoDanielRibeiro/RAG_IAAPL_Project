"""Pydantic request/response schemas for the FastAPI backend."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    documents_count: int
    chat_model: str
    embedding_model: str


class DocumentInfo(BaseModel):
    id: str
    name: str
    size_bytes: int


class UploadResponse(BaseModel):
    documents: list[DocumentInfo]
    message: str


class ChatRequest(BaseModel):
    question: str
    answer_mode: str = "standard"
    chat_history: list[dict] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)


class ChunkInfo(BaseModel):
    source: str
    page: Optional[int] = None
    score: Optional[float] = None
    snippet: str


class ChatResponse(BaseModel):
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
    answer_mode: str
    source_distribution: dict[str, int] = Field(default_factory=dict)
    document_ids: list[str] = Field(default_factory=list)


class SummaryEntry(BaseModel):
    file_name: str
    summary: str
    pages: list[int]


class SummaryResponse(BaseModel):
    summaries: list[SummaryEntry]
