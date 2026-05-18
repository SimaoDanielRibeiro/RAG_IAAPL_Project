"""FastAPI backend package.

Wraps the RAG pipeline (`src.rag`) behind an HTTP API consumed by the
Next.js frontend. Submodules:

- `main`     — FastAPI app entry point + CORS configuration.
- `api`      — HTTP route handlers.
- `services` — process-level singleton that holds the pipeline + state.
- `schemas`  — Pydantic request/response models.
"""
