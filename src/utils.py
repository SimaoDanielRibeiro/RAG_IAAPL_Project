"""Utility helpers for the Streamlit document RAG app."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any


LOGGER_NAME = "pdf_rag_app"


def configure_logging() -> logging.Logger:
    """Configure and return the app logger."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return logging.getLogger(LOGGER_NAME)


def ensure_directory(path: str | Path) -> Path:
    """Create a directory if it does not exist."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def file_sha256(file_bytes: bytes) -> str:
    """Return a stable hash for uploaded file contents."""
    return hashlib.sha256(file_bytes).hexdigest()


def combined_files_sha256(files: list[tuple[str, bytes]]) -> str:
    """Return a stable hash for a set of uploaded files."""
    digest = hashlib.sha256()
    for file_name, file_bytes in sorted(files, key=lambda item: item[0].lower()):
        digest.update(file_name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_bytes)
        digest.update(b"\0")
    return digest.hexdigest()


def safe_collection_name(file_name: str, content_hash: str) -> str:
    """Build a stable and filesystem-safe Chroma collection name."""
    stem = Path(file_name).stem.lower()
    cleaned = "".join(character if character.isalnum() else "-" for character in stem)
    cleaned = cleaned.strip("-") or "document"
    return f"{cleaned[:40]}-{content_hash[:12]}"


def load_json_file(path: str | Path) -> dict[str, Any]:
    """Load JSON data from disk, returning an empty dict when missing or corrupted."""
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Treat unreadable or partially-written files as empty so the app can recover.
        logging.getLogger(LOGGER_NAME).warning(
            "Could not parse JSON at %s; treating as empty.", file_path
        )
        return {}


def save_json_file(path: str | Path, payload: dict[str, Any]) -> None:
    """Save a JSON payload to disk."""
    file_path = Path(path)
    file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
