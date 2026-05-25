# Lumen — Local Document Q&A with Retrieval-Augmented Generation

A local-first document research assistant. Upload PDF, DOCX, TXT, or
Markdown files and ask questions grounded in their contents. Answers
are produced by a fully local RAG pipeline (Ollama + ChromaDB), served
through a FastAPI backend, and consumed by a Next.js chat frontend.

This README focuses on the **RAG pipeline**. The frontend is the
interface the user interacts with; its visual design is not the focus
of this write-up, but the README does explain what it shows and how
to run it.

---

## Table of contents

1. [What this project does](#what-this-project-does)
2. [RAG pipeline overview](#rag-pipeline-overview)
3. [Project structure](#project-structure)
4. [Requirements](#requirements)
5. [Setup](#setup)
6. [Running the project](#running-the-project)
7. [Using the app](#using-the-app)
8. [HTTP API](#http-api)
9. [Configuration knobs](#configuration-knobs)
10. [Troubleshooting](#troubleshooting)

---

## What this project does

Given a small corpus of local documents (up to 10 files, 200 MB each),
Lumen answers natural-language questions about them. Every answer is
grounded in retrieved chunks of the original documents, with explicit
citations (file + page) and a confidence label.

Key design choices:

- **Fully local.** No cloud APIs. The chat model and the embedding
  model both run through Ollama on the user's machine.
- **Hybrid retrieval.** Combines semantic (dense vector) and lexical
  (BM25) retrieval, fused with Reciprocal Rank Fusion (RRF).
- **CrossEncoder reranking.** A small cross-encoder re-scores the
  fused candidate pool before answer generation.
- **Two answer modes.** A concise "standard" mode and a verbose,
  citation-rich "exhaustive" mode.
- **Citation transparency.** In exhaustive mode every paragraph
  carries an inline `[N]` chip that maps 1-to-1 with a card in the
  Evidence panel. Clicking the chip scrolls to the supporting excerpt
  and pulses it.
- **Context window visibility.** The Evidence panel can expand an
  "Additional context the model saw" section listing the neighbor or
  selected-but-uncited chunks that influenced the answer.
- **Source preview.** Each Evidence card has an "Open in source"
  button that opens the original PDF at the cited page inside a
  modal, so claims can be verified in their original layout.
- **OCR fallback** for image-only PDFs (optional — see Setup step 5b).

---

## RAG pipeline overview

The end-to-end flow when a user asks a question:

```
                                +--------------------+
       (upload time)            |  user question     |
                                +---------+----------+
       1. file_storage                   |
       2. pdf_extractor                  | 4. query rewriting
          (+ OCR fallback)               |    (history-aware) +
       3. document_loader                |    multi-query expansion
       4. chunking                       |
            |                            |
            v                            v
       Chroma collection           Generated queries
       + embeddings                  (3 variants)
            |                            |
            +-----------+----------------+
                        |
                        v
         5. hybrid retrieval (retrieval.py)
              - MMR vector search (per query)
              - BM25 keyword search (per query)
              - Reciprocal Rank Fusion across all lists
                        |
                        v
                Fused candidate pool
                        |
                        v
         6. reranking (reranking.py)
              - CrossEncoder ms-marco-MiniLM-L-6-v2
              - LLM fallback if the encoder is unavailable
                        |
                        v
                Top-N selected chunks
                        |
                        v
         7. neighbor expansion (standard mode only)
              - Previous/next chunk per survivor for fuller context
                        |
                        v
         8. context build + answer generation (generation.py)
              - Mode-aware prompt (standard vs exhaustive)
              - Exhaustive: numbered EVIDENCE IDs the LLM cites as [N]
              - Citation validation + retry loop (exhaustive only)
              - Stream answer tokens
                        |
                        v
         9. response shaping (formatting.py + pipeline.py)
              - Citation alignment: keep only chunks the answer cited
                and remap [N]s to a compact 1-based range
              - Context_documents: chunks the LLM saw but did not cite
              - Confidence label (High / Medium / Low)
```

Each stage lives in its own module so the pipeline can be inspected,
tuned, and tested independently:

| Stage | File | Class |
|---|---|---|
| File persistence | [src/rag/file_storage.py](src/rag/file_storage.py) | `FileStorage` |
| PDF layout extraction (+ OCR) | [src/rag/pdf_extractor.py](src/rag/pdf_extractor.py) | (module functions) |
| Document loading | [src/rag/document_loader.py](src/rag/document_loader.py) | (module functions) |
| Chunking | [src/rag/chunking.py](src/rag/chunking.py) | `DocumentChunker` |
| Vector store mgmt | [src/rag/vector_store.py](src/rag/vector_store.py) | `VectorStoreManager` |
| Query rewriting | [src/rag/querying.py](src/rag/querying.py) | `QueryProcessor` |
| Hybrid retrieval | [src/rag/retrieval.py](src/rag/retrieval.py) | `HybridRetriever` |
| Reranking | [src/rag/reranking.py](src/rag/reranking.py) | `DocumentReranker` |
| Answer generation | [src/rag/generation.py](src/rag/generation.py) | `AnswerGenerator` |
| Context formatting | [src/rag/formatting.py](src/rag/formatting.py) | (module functions) |
| Prompts | [src/rag/prompts.py](src/rag/prompts.py) | (module constants) |
| Orchestration | [src/rag/pipeline.py](src/rag/pipeline.py) | `DocumentRAGPipeline` |
| Tuning knobs | [src/rag/config.py](src/rag/config.py) | `RAGConfig` |

---

## Project structure

```text
RAG_Project/
├── backend/                       # FastAPI HTTP layer
│   ├── main.py                    # App entry point + CORS
│   ├── schemas.py                 # Pydantic request/response models
│   ├── api/
│   │   └── routes.py              # /api/* endpoints
│   └── services/
│       └── rag_service.py         # Process-level singleton: pipeline + state
│
├── src/                           # Pipeline source (importable as `src.rag`)
│   ├── utils.py                   # Logging, hashing, JSON IO
│   └── rag/                       # RAG package (see table above)
│
├── frontend/                      # Next.js chat UI
│   ├── App.tsx                    # Top-level layout + state container
│   ├── components/
│   │   ├── ChatPane.tsx           # Message list + citation chips
│   │   ├── Composer.tsx           # Question input
│   │   ├── EvidenceCard.tsx       # One retrieved chunk
│   │   ├── EvidencePanel.tsx      # Right-hand evidence column
│   │   ├── LandingScreen.tsx
│   │   ├── Sidebar.tsx            # Documents + scope selector
│   │   └── SourcePreviewModal.tsx # PDF preview at cited page
│   ├── lib/
│   │   ├── api.ts                 # Backend client
│   │   └── text.ts                # Markdown stripper
│   └── types/index.ts             # Shared TS types
│
├── data/                          # Uploaded documents (gitignored)
├── chroma_db/                     # Persistent vector store (gitignored)
│
├── requirements.txt               # Python dependencies
├── .env.example                   # Sample model configuration
└── README.md
```

---

## Requirements

- **Python 3.10 or newer** (tested on Python 3.13)
- **Node.js 18+** with npm (for the frontend)
- **Ollama** installed and running locally — https://ollama.com/download
- Around **6 GB of disk space** for the Ollama models on first pull.
- **Tesseract OCR** (optional, for scanned PDFs — see step 5b).

The project has been developed on Windows 11. It is OS-independent
(Linux and macOS work the same way), but the command snippets below
use PowerShell. Translate `venv\Scripts\python.exe` to
`venv/bin/python` on Linux / macOS.

---

## Setup

### 1. Clone the repository

```powershell
git clone <repository-url>
cd RAG_Project
```

### 2. Create a Python virtual environment

```powershell
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

This installs the LangChain + Chroma + Ollama bindings, PyMuPDF for
PDF extraction, sentence-transformers for the CrossEncoder reranker,
FastAPI / Uvicorn for the HTTP server, and pytesseract + Pillow for
the optional OCR pass.

### 4. Install frontend dependencies

```powershell
cd frontend
npm install
cd ..
```

### 5. Pull the Ollama models

With Ollama running in the background:

```powershell
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
```

`qwen2.5:7b-instruct` is the chat model that generates answers.
`nomic-embed-text` is the embedding model used to index documents.

### 5b. (Optional) Install Tesseract OCR for scanned PDFs

Image-only PDFs (typical of scanned reports) yield no extractable text
and fall through to an OCR pass. The Python wrapper (`pytesseract`) is
already in `requirements.txt`; the system binary it calls must be
installed separately:

- **Windows:** download the UB Mannheim installer at
  <https://github.com/UB-Mannheim/tesseract/wiki> and add the install
  directory to `PATH`. To OCR Portuguese as well as English, tick the
  "Portuguese" language pack in the installer.
- **macOS:** `brew install tesseract tesseract-lang`
- **Linux:** `sudo apt install tesseract-ocr tesseract-ocr-por`

When Tesseract is missing, the pipeline still works for text-based PDFs —
scanned pages just come back empty and the indexer logs a one-time hint.

### 6. (Optional) Override the default models

Copy `.env.example` to `.env` to choose different Ollama models:

```env
OLLAMA_CHAT_MODEL=qwen2.5:7b-instruct
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

The frontend reads `NEXT_PUBLIC_API_BASE_URL` from
`frontend/.env.local`. For local development that file should
contain:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Running the project

You need **two terminals**, one for the backend and one for the
frontend. Both must be running for the app to be usable.

### Terminal 1 — backend

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Once it boots:

- Health probe: <http://localhost:8000/api/health>
- Interactive API explorer (Swagger): <http://localhost:8000/docs>

The `--reload` flag auto-restarts when you save Python files.

### Terminal 2 — frontend

```powershell
cd frontend
npm run dev
```

Once it boots:

- Open <http://localhost:3000> in your browser.

The frontend is what the user actually interacts with. The backend
on port 8000 only exposes the HTTP API.

---

## Using the app

Open <http://localhost:3000>. The Next.js frontend provides:

- **An upload sidebar** to add PDF / DOCX / TXT / MD documents. Files
  are saved under `data/` on disk and indexed into ChromaDB. Click a
  document to scope retrieval to it; click again to clear the scope.
- **A chat panel** where you ask questions. Tokens stream in as the
  model generates them. Citation chips (`[1]`, `[2]`, ...) appear in
  exhaustive-mode answers; clicking one highlights the matching card
  in the Evidence panel.
- **An answer-mode selector** in the sidebar with two options:
  - *Standard* — concise prose (2–4 sentences), no inline citations.
    The Evidence panel still lists the retrieved chunks.
  - *Exhaustive* — multi-paragraph answers with `[N]` citations at
    each paragraph end, validated and remapped server-side so chip
    numbers match Evidence card numbers exactly.
- **An evidence panel** on the right that shows:
  - The standalone question + multi-query rewrites used for retrieval.
  - File citations (one per source, with the pages used).
  - A source-distribution chart when multiple files contributed.
  - The retrieved chunks themselves, each with file name, page number,
    word count, retrieved excerpt, rerank relevance score, and a
    hover-revealed action bar (copy, expand, open-in-source).
  - A collapsible **"Additional context the model saw"** section
    listing chunks the LLM read but the final answer didn't cite
    (neighbors in standard mode, selected-but-uncited in exhaustive).
- **A source-preview modal** that opens when you click *Open in
  source* on any Evidence card. PDFs are rendered inline with the
  cited page anchored; other formats fall back to a downloadable
  preview of the retrieved excerpt.
- **A "Summarize documents" CTA** that produces a bullet-point
  summary for every active document via a dedicated endpoint.

Typical flow:

1. Upload one or more documents from the sidebar.
2. Wait for the indexing notification.
3. Ask a question in the chat. Toggle answer mode if needed.
4. Click any `[N]` chip to jump to the supporting Evidence card, or
   click *Open in source* on a card to verify the claim against the
   original document.

---

## HTTP API

The backend is consumed by the frontend but can also be called
directly via `curl` or the interactive Swagger UI at `/docs`.

| Method | Path                                | Description                                |
|--------|-------------------------------------|--------------------------------------------|
| GET    | `/api/health`                       | Backend + model status                     |
| GET    | `/api/documents`                    | List active documents                      |
| POST   | `/api/documents/upload`             | Upload + index files                       |
| GET    | `/api/documents/{id}/file`          | Serve the original file (for preview)      |
| DELETE | `/api/documents/{id}`               | Remove one document                        |
| DELETE | `/api/documents`                    | Remove all documents                       |
| POST   | `/api/chat`                         | Ask a question (non-streaming)             |
| POST   | `/api/chat/stream`                  | Ask a question (streaming, NDJSON)         |
| POST   | `/api/summary`                      | Summarize all (or selected) documents      |

Full schemas in [backend/schemas.py](backend/schemas.py).

---

## Configuration knobs

All tuning parameters live in [src/rag/config.py](src/rag/config.py)
as a frozen dataclass (`RAGConfig`). The most impactful knobs:

| Knob                              | Default   | Effect                                          |
|-----------------------------------|-----------|-------------------------------------------------|
| `chunk_size` / `chunk_overlap`    | 500 / 100 | Indexing granularity                            |
| `vector_top_k`                    | 8         | Top-K for standard-mode vector retrieval        |
| `exhaustive_top_k`                | 12        | Top-K for exhaustive-mode vector retrieval      |
| `mmr_lambda`                      | 0.7       | MMR diversity vs relevance trade-off            |
| `rrf_k`                           | 60        | Reciprocal Rank Fusion smoothing constant       |
| `rrf_pool_multiplier`             | 4         | Fused candidate pool size = top_k × multiplier  |
| `standard_final_chunks`           | 6         | Chunks passed to the LLM in standard mode       |
| `exhaustive_final_chunks`         | 10        | Chunks passed to the LLM in exhaustive mode     |
| `weak_evidence_average_threshold` | 6.5       | Fallback gate (LLM-fallback path only)          |
| `minimum_supporting_chunks`       | 2         | Minimum chunks needed for an answer             |
| `index_version`                   | `"hybrid-rag-v4-layout"` | Bumped when index layout changes |

Changing `chunk_size`, `chunk_overlap`, or `index_version` causes the
next upload to rebuild its Chroma collection.

---

## Troubleshooting

**`ollama serve` is not running or models are not pulled.** The
backend will return `502` / `500` on every chat request. Confirm with
`ollama list` and `curl http://localhost:11434/api/tags`.

**Slow first response.** The CrossEncoder is downloaded lazily on
first use (~22 MB) and the Chroma collection is built on first
upload. Subsequent calls reuse both.

**`Indexing failed` on upload.** Check that the file is one of
`.pdf / .docx / .txt / .md` and smaller than 200 MB. Scanned PDFs work
only if Tesseract OCR is installed (see step 5b in *Setup*); without
it, image-only pages produce no text and the indexer rejects the file.

**Port 8000 is busy.** Stop the previous Uvicorn process or pass a
different port: `--port 8001` (and update
`NEXT_PUBLIC_API_BASE_URL` accordingly).

**`chroma_db/` growing too large.** It is safe to delete the
directory; the next upload rebuilds it. The on-disk index is a cache,
not a primary store — uploaded documents live under `data/`.

**Frontend cannot reach the backend.** Confirm both processes are
running, then check that `frontend/.env.local` has
`NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

**PDF preview shows an empty page.** Some browsers refuse to render
PDFs inside iframes when extensions block them. Use the *Open in new
tab* button in the modal header to view the file directly.
