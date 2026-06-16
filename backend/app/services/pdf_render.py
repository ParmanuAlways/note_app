"""Render document pages to images for the VLM (FR-8: all pages processed).

PDFs are rasterised page-by-page with PyMuPDF; image uploads pass through
unchanged. Output is PNG bytes per page — the format the extraction client
sends to the model.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

# 200 DPI balances legibility for the model against image size.
_ZOOM = 200 / 72


def render_pages(data: bytes, filename: str) -> list[bytes]:
    if Path(filename).suffix.lower() != ".pdf":
        return [data]  # already an image
    pages: list[bytes] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        matrix = fitz.Matrix(_ZOOM, _ZOOM)
        for page in doc:
            pages.append(page.get_pixmap(matrix=matrix).tobytes("png"))
    return pages
