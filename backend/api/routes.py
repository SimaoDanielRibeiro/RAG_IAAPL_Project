"""FastAPI route definitions."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from backend.schemas import (
    ChatRequest,
    ChatResponse,
    ChunkInfo,
    DocumentInfo,
    HealthResponse,
    SummaryEntry,
    SummaryResponse,
    UploadResponse,
)
from backend.services.rag_service import (
    ACCEPTED_SUFFIXES,
    MAX_FILE_SIZE_MB,
    MAX_FILES_PER_UPLOAD,
    rag_service,
)

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------
@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        documents_count=len(rag_service.list_documents()),
        chat_model=rag_service.chat_model,
        embedding_model=rag_service.embedding_model,
    )


# ------------------------------------------------------------------
# Documents
# ------------------------------------------------------------------
@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents() -> list[DocumentInfo]:
    return [
        DocumentInfo(id=d.id, name=d.name, size_bytes=d.size_bytes)
        for d in rag_service.list_documents()
    ]


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_documents(files: list[UploadFile] = File(...)) -> UploadResponse:
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files. Maximum {MAX_FILES_PER_UPLOAD} per upload.",
        )

    payloads: list[tuple[str, bytes]] = []
    for file in files:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ACCEPTED_SUFFIXES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported type '{suffix}'. Accepted: {', '.join(sorted(ACCEPTED_SUFFIXES))}.",
            )
        content = await file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{file.filename}' is {size_mb:.1f} MB; max is {MAX_FILE_SIZE_MB} MB.",
            )
        payloads.append((file.filename or "upload", content))

    try:
        new_records = await asyncio.to_thread(rag_service.add_documents, payloads)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        LOGGER.exception("Indexing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {exc}",
        )

    all_docs = rag_service.list_documents()
    return UploadResponse(
        documents=[DocumentInfo(id=d.id, name=d.name, size_bytes=d.size_bytes) for d in all_docs],
        message=f"Indexed {len(new_records)} file(s). {len(all_docs)} active.",
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def remove_document(document_id: str) -> Response:
    try:
        await asyncio.to_thread(rag_service.remove_document, document_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        LOGGER.exception("Remove document failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return Response(status_code=204)


@router.delete("/documents", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def remove_all_documents() -> Response:
    rag_service.remove_all_documents()
    return Response(status_code=204)


# ------------------------------------------------------------------
# Chat
# ------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if not rag_service.list_documents():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents indexed. Upload documents first.",
        )
    try:
        result = await asyncio.to_thread(
            rag_service.answer_question, req.question, req.answer_mode, req.chat_history
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        LOGGER.exception("Chat failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    chunks = [
        ChunkInfo(
            source=doc.metadata.get("source", ""),
            page=doc.metadata.get("page"),
            score=doc.metadata.get("rerank_score"),
            snippet=doc.page_content[:600],
        )
        for doc in result.get("documents", [])
    ]

    return ChatResponse(
        answer=result.get("answer", ""),
        confidence=result.get("confidence", "Low"),
        sources=result.get("sources", []),
        pages=result.get("pages", []),
        citations=result.get("citations", []),
        chunks_used=result.get("chunks_used", 0),
        average_score=result.get("average_score"),
        queries=result.get("queries", []),
        retrieval_question=result.get("retrieval_question", req.question),
        documents=chunks,
        answer_mode=result.get("answer_mode", req.answer_mode),
    )


# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
@router.post("/summary", response_model=SummaryResponse)
async def summary() -> SummaryResponse:
    if not rag_service.list_documents():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents indexed. Upload documents first.",
        )
    try:
        result = await asyncio.to_thread(rag_service.summarize)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        LOGGER.exception("Summary failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    return SummaryResponse(
        summaries=[
            SummaryEntry(
                file_name=s.get("file_name", ""),
                summary=s.get("summary", ""),
                pages=s.get("pages", []),
            )
            for s in result.get("summaries", [])
        ]
    )
