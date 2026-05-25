"""FastAPI route definitions."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, Body, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response, StreamingResponse

from src.rag.config import FALLBACK_ANSWER

from backend.schemas import (
    ChatRequest,
    ChatResponse,
    ChunkInfo,
    DocumentInfo,
    HealthResponse,
    SummaryEntry,
    SummaryRequest,
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


_MIME_TYPES: dict[str, str] = {
    ".pdf":  "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt":  "text/plain; charset=utf-8",
    ".md":   "text/markdown; charset=utf-8",
}


@router.get("/documents/{document_id}/file")
async def get_document_file(document_id: str) -> FileResponse:
    """Serve the original uploaded file so the frontend can render a preview.

    The path comes from the in-memory document record (set at upload time by
    `FileStorage` after sanitisation) — never from the request — so this route
    cannot be tricked into reading arbitrary files on disk.
    """
    record = next(
        (document for document in rag_service.list_documents() if document.id == document_id),
        None,
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )
    path = Path(record.path)
    if not path.exists() or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File for document '{document_id}' is no longer on disk.",
        )
    media_type = _MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")
    # `inline` keeps the file viewable in the iframe instead of triggering a
    # download. Pass the original name so the browser shows it in any "save as"
    # action initiated by the user.
    return FileResponse(
        path=str(path),
        media_type=media_type,
        filename=record.name,
        headers={"Content-Disposition": f'inline; filename="{record.name}"'},
    )


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
            rag_service.answer_question,
            req.question,
            req.answer_mode,
            req.chat_history,
            req.document_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        LOGGER.exception("Chat failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    source_to_id = _source_to_document_id()

    def to_chunk_info(doc) -> ChunkInfo:
        source = doc.metadata.get("source", "")
        return ChunkInfo(
            source=source,
            page=doc.metadata.get("page"),
            score=doc.metadata.get("rerank_score"),
            score_scale=doc.metadata.get("rerank_score_scale"),
            snippet=doc.page_content,
            document_id=source_to_id.get(source),
        )

    chunks = [to_chunk_info(doc) for doc in result.get("documents", [])]
    context_chunks = [to_chunk_info(doc) for doc in result.get("context_documents", [])]

    source_distribution: dict[str, int] = {}
    for chunk in chunks:
        source_distribution[chunk.source] = source_distribution.get(chunk.source, 0) + 1

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
        context_documents=context_chunks,
        answer_mode=result.get("answer_mode", req.answer_mode),
        source_distribution=source_distribution,
        document_ids=req.document_ids,
    )


# ------------------------------------------------------------------
# Chat (streaming)
# ------------------------------------------------------------------
def _source_to_document_id() -> dict[str, str]:
    """Map source filename → active document_id for chunk-to-PDF linking."""
    return {document.name: document.id for document in rag_service.list_documents()}


def _doc_to_chunk_dict(doc, source_to_id: dict[str, str]) -> dict:
    """Render one LangChain Document as the JSON shape the UI consumes."""
    source = doc.metadata.get("source", "")
    return {
        "source":      source,
        "page":        doc.metadata.get("page"),
        "score":       doc.metadata.get("rerank_score"),
        "score_scale": doc.metadata.get("rerank_score_scale"),
        "snippet":     doc.page_content,
        "document_id": source_to_id.get(source),
    }


def _chunks_payload(documents: list) -> tuple[list[dict], dict[str, int]]:
    """Shape retrieved documents into the JSON-serializable structure used
    by both the streaming metadata event and the non-streaming response."""
    source_to_id = _source_to_document_id()
    chunks = [_doc_to_chunk_dict(doc, source_to_id) for doc in documents]
    distribution: dict[str, int] = {}
    for c in chunks:
        distribution[c["source"]] = distribution.get(c["source"], 0) + 1
    return chunks, distribution


def _context_chunks_payload(documents: list) -> list[dict]:
    """Shape the additional-context document list (no distribution needed)."""
    source_to_id = _source_to_document_id()
    return [_doc_to_chunk_dict(doc, source_to_id) for doc in documents]


_WORD_CHUNK_PATTERN = re.compile(r"\S+\s*|\s+")


def _word_chunks(text: str) -> list[str]:
    """Split text into word-sized chunks for simulated streaming.

    Preserves all whitespace (including newlines) so the streamed answer is
    byte-identical to the final string when concatenated on the frontend.
    """
    if not text:
        return []
    return _WORD_CHUNK_PATTERN.findall(text) or [text]


def _metadata_payload(
    req: ChatRequest,
    result: dict,
    chunks: list[dict],
    distribution: dict[str, int],
    context_chunks: list[dict] | None = None,
) -> dict:
    return {
        "confidence":          result.get("confidence", "Low"),
        "sources":             result.get("sources", []),
        "pages":               result.get("pages", []),
        "citations":           result.get("citations", []),
        "chunks_used":         result.get("chunks_used", 0),
        "average_score":       result.get("average_score"),
        "queries":             result.get("queries", []),
        "retrieval_question":  result.get("retrieval_question", req.question),
        "documents":           chunks,
        "context_documents":   context_chunks or [],
        "answer_mode":         result.get("answer_mode", req.answer_mode),
        "source_distribution": distribution,
        "document_ids":        req.document_ids,
    }


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    if not rag_service.list_documents():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents indexed. Upload documents first.",
        )

    async def event_stream():
        def ndjson(event: dict) -> str:
            return json.dumps(event, default=str) + "\n"

        try:
            prep = await asyncio.to_thread(
                rag_service.prepare_answer,
                req.question,
                req.answer_mode,
                req.chat_history,
                req.document_ids,
            )
        except ValueError as exc:
            yield ndjson({"type": "error", "message": str(exc)})
            return
        except Exception as exc:
            LOGGER.exception("Chat stream prepare failed")
            yield ndjson({"type": "error", "message": str(exc)})
            return

        if prep.get("fallback"):
            chunks, distribution = _chunks_payload(prep.get("documents", []))
            context_chunks = _context_chunks_payload(prep.get("context_documents", []))
            metadata = _metadata_payload(req, prep, chunks, distribution, context_chunks)
            yield ndjson({"type": "metadata", "data": metadata})
            yield ndjson({"type": "token", "text": FALLBACK_ANSWER})
            yield ndjson({"type": "done"})
            return

        try:
            if req.answer_mode == "exhaustive":
                # Exhaustive generation is synchronous because the citation
                # validation + retry loop and `align_numbered_citations_to_documents`
                # both need the FULL answer before they can run. To still give
                # the frontend a typewriter feel, we emit the finalized answer
                # in word-sized chunks with a tiny delay between them.
                answer = await asyncio.to_thread(
                    rag_service.answer_from_prepared,
                    prep["context"],
                    prep["retrieval_question"],
                    req.answer_mode,
                    prep.get("documents", []),
                )
                finalized = await asyncio.to_thread(
                    rag_service.finalize_exhaustive_response,
                    {k: v for k, v in prep.items() if k != "fallback"},
                    answer,
                )
                chunks, distribution = _chunks_payload(finalized.get("documents", []))
                context_chunks = _context_chunks_payload(
                    finalized.get("context_documents", [])
                )
                metadata = _metadata_payload(
                    req, finalized, chunks, distribution, context_chunks
                )
                yield ndjson({"type": "metadata", "data": metadata})

                final_answer = finalized.get("answer", answer)
                for piece in _word_chunks(final_answer):
                    yield ndjson({"type": "token", "text": piece})
                    await asyncio.sleep(0.012)
            else:
                chunks, distribution = _chunks_payload(prep.get("documents", []))
                context_chunks = _context_chunks_payload(
                    prep.get("context_documents", [])
                )
                metadata = _metadata_payload(
                    req, prep, chunks, distribution, context_chunks
                )
                yield ndjson({"type": "metadata", "data": metadata})
                async for token in rag_service.astream_answer(
                    prep["context"], prep["retrieval_question"], req.answer_mode
                ):
                    yield ndjson({"type": "token", "text": token})
        except Exception as exc:
            LOGGER.exception("Chat stream generation failed")
            yield ndjson({"type": "error", "message": str(exc)})
            return

        yield ndjson({"type": "done"})

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
@router.post("/summary", response_model=SummaryResponse)
async def summary(req: SummaryRequest | None = Body(default=None)) -> SummaryResponse:
    if not rag_service.list_documents():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents indexed. Upload documents first.",
        )
    try:
        result = await asyncio.to_thread(
            rag_service.summarize,
            req.document_ids if req else [],
        )
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
