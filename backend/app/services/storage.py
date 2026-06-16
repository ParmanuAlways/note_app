"""Document storage on the server's filesystem (FR-27): the original upload is
the record, kept under a per-owner directory. Also computes the content hash
used for stage-1 duplicate detection (FR-3)."""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

from app.config import get_settings

# Accepted formats (FR-1). Content-type and extension are both checked since
# scanners set inconsistent MIME types.
ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png", "image/tiff"}
ALLOWED_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(name: str) -> str:
    return _SAFE.sub("_", Path(name).name) or "upload"


def is_accepted(filename: str, content_type: str | None) -> bool:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return False
    # Trust the extension; accept if MIME is missing or matches the allow-list.
    return content_type is None or content_type in ALLOWED_MIME or content_type == "application/octet-stream"


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def page_count(data: bytes, filename: str) -> int:
    """Pages for a PDF (for multi-page support, FR-1); 1 for images."""
    if Path(filename).suffix.lower() != ".pdf":
        return 1
    try:
        from pypdf import PdfReader

        return len(PdfReader(io.BytesIO(data)).pages)
    except Exception:  # noqa: BLE001 — unreadable/odd PDFs still store fine
        return 1


def save(owner_id: str, document_id: str, filename: str, data: bytes) -> str:
    """Write the original file and return its stored path."""
    root = Path(get_settings().storage_root) / owner_id / "documents"
    root.mkdir(parents=True, exist_ok=True)
    dest = root / f"{document_id}__{_safe_name(filename)}"
    dest.write_bytes(data)
    return str(dest)
