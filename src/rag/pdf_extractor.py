"""Layout-aware PDF extraction using PyMuPDF.

Returns one structured page string per PDF page. Downstream chunking uses
the inline markers to split along heading boundaries:

- Lines starting with ``# `` are headings.
- Lines starting with ``[Caption] `` are figure / table captions.
- Markdown pipe tables (``| a | b |``) represent detected tables.
- Anything else is paragraph prose.

Blocks are emitted in reading order (top-to-bottom, then left-to-right),
which preserves single-column flow and works reasonably for two-column
academic layouts. Text that lives inside a detected table bbox is dropped
to avoid duplicating cell content as loose paragraphs.

OCR fallback: pages that yield almost no text (typically image-only scans)
are passed through pytesseract on a high-DPI render of the page. The
feature is best-effort — if pytesseract is not installed, or the Tesseract
binary is not on PATH, the page is left as-is and a one-time hint is logged.
"""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from statistics import median
from typing import Any, Optional

import fitz  # PyMuPDF

try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except ImportError:
    pytesseract = None  # type: ignore[assignment]
    Image = None        # type: ignore[assignment]
    _OCR_AVAILABLE = False

LOGGER = logging.getLogger(__name__)

# Pages with fewer than this many extractable characters are treated as
# image-only and routed through OCR. Empty PDFs naturally fall under this
# threshold; the OCR call will just return "" for them.
_OCR_MIN_TEXT_CHARS = 30
# 200 DPI is the sweet spot for Tesseract on body text — higher is slower
# without measurable accuracy gains; lower starts to miss small fonts.
_OCR_RENDER_DPI = 200

_TESSERACT_MISSING_NOTICE_LOGGED = False

# Caption prefixes the extractor recognises, English + Iberian variants. The
# match is case-insensitive and anchored to the start of the block so we
# don't classify body sentences containing the word "figure".
_CAPTION_RE = re.compile(
    r"^\s*(?:figure|fig\.?|table|tab\.?|figura|tabela|esquema|listing|listagem)\s*\d",
    re.IGNORECASE,
)

# Numbered heading patterns: "1.", "1.1", "2.3.4", optionally followed by a
# capitalised word so we don't catch things like "1. however..." that are
# really list items.
_NUMBERED_HEADING_RE = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s+\S")

# PyMuPDF span flag bit for bold faces. See `flags` field docs.
_BOLD_FLAG = 16


def extract_pages(path: Path) -> list[str]:
    """Return a structured text string for every page in the PDF.

    Pages that come back nearly empty are sent to OCR (when available) so
    scanned PDFs still produce indexable text.
    """
    pages: list[str] = []
    with fitz.open(str(path)) as doc:
        for page_index in range(doc.page_count):
            page = doc[page_index]
            try:
                rendered = _extract_page(page)
            except Exception:
                LOGGER.exception(
                    "PyMuPDF extraction failed for page %d of %s; falling back to plain text.",
                    page_index,
                    path.name,
                )
                rendered = page.get_text("text")

            if len(rendered.strip()) < _OCR_MIN_TEXT_CHARS:
                ocr_text = _ocr_page(page, page_index, path.name)
                if ocr_text.strip():
                    rendered = ocr_text

            pages.append(rendered)
    return pages


def _ocr_page(page: "fitz.Page", page_index: int, file_name: str) -> str:
    """Render the page as an image and run Tesseract on it.

    Returns ``""`` when OCR is unavailable or fails. Never raises — the caller
    treats an empty OCR result as "no text on this page".
    """
    global _TESSERACT_MISSING_NOTICE_LOGGED

    if not _OCR_AVAILABLE:
        if not _TESSERACT_MISSING_NOTICE_LOGGED:
            LOGGER.info(
                "pytesseract / Pillow are not installed; skipping OCR for "
                "image-only PDF pages. Install them (and the Tesseract binary) "
                "to enable scanned-PDF support."
            )
            _TESSERACT_MISSING_NOTICE_LOGGED = True
        return ""

    try:
        zoom = _OCR_RENDER_DPI / 72.0
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    except Exception as error:
        LOGGER.warning(
            "Could not render page %d of %s for OCR: %s",
            page_index + 1, file_name, error,
        )
        return ""

    # Try Portuguese + English first since the project mixes languages; fall
    # back to whatever the local Tesseract install ships (usually 'eng').
    for lang in ("eng+por", None):
        try:
            text = pytesseract.image_to_string(image, lang=lang) if lang else \
                pytesseract.image_to_string(image)
            if text.strip():
                LOGGER.info(
                    "OCR extracted %d chars for page %d of %s (lang=%s).",
                    len(text.strip()), page_index + 1, file_name, lang or "default",
                )
            return text
        except pytesseract.TesseractNotFoundError:
            if not _TESSERACT_MISSING_NOTICE_LOGGED:
                LOGGER.warning(
                    "Tesseract binary not found on PATH; install it to enable "
                    "OCR for scanned PDFs (see README). pytesseract is installed "
                    "but the binary is the system component it wraps."
                )
                _TESSERACT_MISSING_NOTICE_LOGGED = True
            return ""
        except pytesseract.TesseractError as error:
            # Language pack missing (eg. 'por.traineddata') — retry without lang.
            LOGGER.debug(
                "Tesseract error with lang=%s on page %d of %s: %s",
                lang, page_index + 1, file_name, error,
            )
            continue
        except Exception as error:
            LOGGER.warning(
                "OCR failed for page %d of %s: %s",
                page_index + 1, file_name, error,
            )
            return ""
    return ""


def _extract_page(page: "fitz.Page") -> str:
    """Build the structured text for one page."""
    table_records = _extract_tables(page)
    raw_dict       = page.get_text("dict")
    median_size    = _median_font_size(raw_dict)

    blocks: list[dict[str, Any]] = []
    for block in raw_dict.get("blocks", []):
        if block.get("type", 1) != 0:        # 0 = text, 1 = image
            continue
        bbox = block.get("bbox")
        if not bbox or _inside_any_table(bbox, table_records):
            continue
        text, max_size, is_bold = _block_text_metrics(block)
        text = text.strip()
        if not text:
            continue
        blocks.append({
            "kind": _classify(text, max_size, is_bold, median_size),
            "text": text,
            "bbox": tuple(bbox),
        })

    for bbox, markdown in table_records:
        blocks.append({"kind": "table", "text": markdown, "bbox": bbox})

    # Reading order: y first, then x. Rounded so tiny vertical jitter doesn't
    # break the sort.
    blocks.sort(key=lambda b: (round(b["bbox"][1], 1), round(b["bbox"][0], 1)))

    return _render(blocks)


# ----------------------------------------------------------------------
# Tables
# ----------------------------------------------------------------------
def _extract_tables(page: "fitz.Page") -> list[tuple[tuple[float, ...], str]]:
    """Detect tables and convert them to markdown. Empty tables are dropped."""
    out: list[tuple[tuple[float, ...], str]] = []
    try:
        tables = page.find_tables()
    except Exception:
        return out
    for tbl in getattr(tables, "tables", []) or []:
        markdown = _table_to_markdown(tbl)
        if markdown:
            out.append((tuple(tbl.bbox), markdown))
    return out


def _table_to_markdown(table: Any) -> str:
    try:
        rows = table.extract()
    except Exception:
        return ""
    if not rows:
        return ""
    cleaned = [[_clean_cell(cell) for cell in row] for row in rows]
    cleaned = [row for row in cleaned if any(cell for cell in row)]
    if not cleaned:
        return ""

    header = cleaned[0]
    body   = cleaned[1:]
    width  = len(header)
    lines: list[str] = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in body:
        if len(row) < width:
            row = row + [""] * (width - len(row))
        lines.append("| " + " | ".join(row[:width]) + " |")
    return "\n".join(lines)


def _clean_cell(cell: Optional[str]) -> str:
    if not cell:
        return ""
    return re.sub(r"\s+", " ", str(cell)).strip().replace("|", r"\|")


# ----------------------------------------------------------------------
# Block metrics + classification
# ----------------------------------------------------------------------
def _median_font_size(raw_dict: dict) -> float:
    sizes: list[float] = []
    for block in raw_dict.get("blocks", []):
        if block.get("type", 1) != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                size = span.get("size", 0)
                if size:
                    sizes.append(size)
    return median(sizes) if sizes else 10.0


def _block_text_metrics(block: dict) -> tuple[str, float, bool]:
    """Return (joined text, max span size, any span bold)."""
    out_lines: list[str] = []
    max_size  = 0.0
    is_bold   = False
    for line in block.get("lines", []):
        parts: list[str] = []
        for span in line.get("spans", []):
            text = span.get("text", "")
            if not text:
                continue
            parts.append(text)
            size = span.get("size", 0) or 0
            if size > max_size:
                max_size = size
            if (span.get("flags", 0) or 0) & _BOLD_FLAG:
                is_bold = True
        if parts:
            out_lines.append("".join(parts))
    return ("\n".join(out_lines), max_size, is_bold)


def _classify(text: str, font_size: float, is_bold: bool, median_size: float) -> str:
    """Decide whether the block is a heading, caption, or paragraph."""
    if _CAPTION_RE.match(text):
        return "caption"

    char_count = len(text)
    line_count = text.count("\n") + 1
    is_short   = char_count <= 120 and line_count <= 2

    if is_short and font_size >= median_size + 1.5:
        return "heading"
    if is_short and is_bold and char_count <= 80:
        return "heading"
    if is_short and _NUMBERED_HEADING_RE.match(text):
        return "heading"
    return "paragraph"


# ----------------------------------------------------------------------
# Layout helpers
# ----------------------------------------------------------------------
def _inside_any_table(
    bbox: tuple[float, ...],
    table_records: list[tuple[tuple[float, ...], str]],
) -> bool:
    return any(_inside(bbox, tb) for tb, _ in table_records)


def _inside(
    inner: tuple[float, ...],
    outer: tuple[float, ...],
) -> bool:
    """True when `inner` sits inside `outer` with a small tolerance."""
    ix0, iy0, ix1, iy1 = inner
    ox0, oy0, ox1, oy1 = outer
    slack = 1.5
    return (
        ix0 >= ox0 - slack
        and iy0 >= oy0 - slack
        and ix1 <= ox1 + slack
        and iy1 <= oy1 + slack
    )


# ----------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------
def _render(blocks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for block in blocks:
        text = block["text"].strip()
        if not text:
            continue
        kind = block["kind"]
        if kind == "heading":
            parts.append(f"# {text}")
        elif kind == "caption":
            parts.append(f"[Caption] {text}")
        else:
            parts.append(text)
    return "\n\n".join(parts)
