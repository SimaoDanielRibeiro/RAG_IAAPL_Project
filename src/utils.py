"""Generic utility helpers used by the UI and the RAG package."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any


LOGGER_NAME = "pdf_rag_app"


def configure_logging() -> logging.Logger:
    """Configure and return the app logger.

    Idempotent: calling this multiple times is safe; `logging.basicConfig`
    is a no-op after the root handler is configured.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return logging.getLogger(LOGGER_NAME)


def ensure_directory(path: str | Path) -> Path:
    """Create a directory if it does not exist and return the resolved Path."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def file_sha256(file_bytes: bytes) -> str:
    """Return a hex-encoded SHA-256 of one file's contents."""
    return hashlib.sha256(file_bytes).hexdigest()


def combined_files_sha256(files: list[tuple[str, bytes]]) -> str:
    """Return a stable hex-encoded SHA-256 across a set of uploaded files.

    Files are sorted by lowercase name before hashing so the digest is
    independent of upload order.
    """
    digest = hashlib.sha256()
    for file_name, file_bytes in sorted(files, key=lambda item: item[0].lower()):
        digest.update(file_name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_bytes)
        digest.update(b"\0")
    return digest.hexdigest()


def load_json_file(path: str | Path) -> dict[str, Any]:
    """Load JSON data from disk, returning {} when missing, unreadable, or corrupted."""
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logging.getLogger(LOGGER_NAME).warning(
            "Could not parse JSON at %s; treating as empty.", file_path
        )
        return {}


def save_json_file(path: str | Path, payload: dict[str, Any]) -> None:
    """Atomically save a JSON payload to disk.

    Writes to a temporary file in the same directory and renames over the
    target so a crash mid-write cannot leave a half-written file.
    """
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(file_path)
