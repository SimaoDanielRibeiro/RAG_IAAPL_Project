"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router

app = FastAPI(
    title="Lumen API",
    description="Local-first document Q&A backend powered by Ollama.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    # Any port on localhost / 127.0.0.1, so the frontend keeps working when
    # port 3000 is taken and Next.js runs on another one.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root() -> dict:
    return {"message": "Lumen API is running. Visit /docs for the API explorer."}
