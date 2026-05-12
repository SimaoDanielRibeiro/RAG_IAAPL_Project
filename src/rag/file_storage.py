"""Safe file persistence for uploaded documents."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from src.rag.document_loader import SUPPORTED_SUFFIXES


class FileStorage:
    """Save uploaded files without trusting user-provided file paths.

    Responsibilities:
    - Reject empty payloads.
    - Strip path components from browser-supplied filenames (path traversal guard).
    - Reject unsupported extensions.
    - When a name collides, only overwrite if content matches; otherwise pick a
      unique suffix so two distinct uploads don't clobber each other.
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def save_one(self, file_name: str, file_bytes: bytes) -> Path:
        """Save one uploaded file using a sanitized, non-colliding name.

        Returns the path the bytes were written to (or the path of an existing
        identical file if the upload duplicates one already on disk).
        """
        if not file_bytes:
            raise ValueError(f"'{file_name}' is empty.")

        safe_name = self._safe_file_name(file_name)
        destination = self._unique_destination(safe_name, file_bytes)
        if destination.exists():
            return destination
        destination.write_bytes(file_bytes)
        return destination

    def save_many(self, files: list[tuple[str, bytes]]) -> list[Path]:
        """Save multiple uploaded files and return their local paths."""
        if not files:
            raise ValueError("At least one file is required.")
        return [self.save_one(file_name, file_bytes) for file_name, file_bytes in files]

    def _safe_file_name(self, file_name: str) -> str:
        """Convert a browser-provided filename into a local filename only."""
        raw_name = Path(file_name).name.strip()
        if not raw_name:
            raise ValueError("Uploaded file name is missing.")

        stem = Path(raw_name).stem
        suffix = Path(raw_name).suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise ValueError(
                f"Unsupported file type: '{suffix}'. "
                f"Supported types: {sorted(SUPPORTED_SUFFIXES)}."
            )

        safe_stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", stem).strip(" ._")
        safe_stem = safe_stem or "uploaded_document"
        return f"{safe_stem[:120]}{suffix}"

    def _unique_destination(self, file_name: str, file_bytes: bytes) -> Path:
        """Avoid overwriting different files that share a name.

        Compares content hashes to detect duplicates rather than reading the
        full file twice (cheap for small files, much cheaper for large PDFs).
        """
        incoming_digest = hashlib.sha256(file_bytes).hexdigest()
        destination = self.data_dir / file_name
        if not destination.exists():
            return destination
        if self._digest_of(destination) == incoming_digest:
            return destination

        stem = destination.stem
        suffix = destination.suffix
        counter = 1
        while True:
            candidate = self.data_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            if self._digest_of(candidate) == incoming_digest:
                return candidate
            counter += 1

    @staticmethod
    def _digest_of(path: Path) -> str:
        """Stream a file's SHA-256 without loading it fully into memory."""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(65536), b""):
                digest.update(block)
        return digest.hexdigest()
