# Lumen - Local Document Q&A

Lumen is a local-first document research assistant. Upload PDF, DOCX, TXT, or Markdown files, then ask questions grounded in those documents. The app uses a Next.js frontend, a FastAPI backend, the existing Python RAG pipeline, ChromaDB, and Ollama.

## Requirements

- Python 3.10+
- Node.js 18+ with npm
- Ollama installed and running

## Setup

From the project root:

```powershell
cd C:\Users\simao\Desktop\RAG_Project
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Pull the local models:

```powershell
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

Optional: copy `.env.example` to `.env` and edit the model names:

```env
OLLAMA_CHAT_MODEL=llama3.2:3b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

## Run

Use two terminals.

Terminal 1 - backend:

```powershell
cd C:\Users\simao\Desktop\RAG_Project
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend checks:

- App status: http://localhost:8000/api/health
- API docs: http://localhost:8000/docs

Terminal 2 - frontend:

```powershell
cd C:\Users\simao\Desktop\RAG_Project\frontend
npm install
npm run dev
```

Open the web app:

- http://localhost:3000

The frontend calls the backend through `NEXT_PUBLIC_API_BASE_URL`. For local development, `frontend/.env.local` should contain:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Use

1. Open http://localhost:3000.
2. Upload documents from the left sidebar.
3. Wait for indexing to finish.
4. Ask questions in the chat.
5. Use the Evidence panel to inspect retrieved chunks, citations, query rewrites, confidence, pages, and sources.
6. Use the answer mode selector for either standard Q&A or exhaustive extraction.
7. Use Summarize documents to generate document summaries.

## API

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Backend and model status |
| GET | `/api/documents` | List active documents |
| POST | `/api/documents/upload` | Upload and index files |
| DELETE | `/api/documents/{id}` | Remove one document |
| DELETE | `/api/documents` | Remove all documents |
| POST | `/api/chat` | Ask a question |
| POST | `/api/summary` | Summarize active documents |

## Project Structure

```text
backend/
  main.py
  schemas.py
  api/
    routes.py
  services/
    rag_service.py
frontend/
  app/
  components/
  lib/
  types/
src/
  rag/
data/
chroma_db/
requirements.txt
```

## Notes

- The supported interface is FastAPI + Next.js.
- Keep `data/` and `chroma_db/` at the project root so the backend can reuse document uploads and Chroma indexes.
- If port 8000 shows an unexpected page or fails to start, stop the old process first, then start the backend command above.
