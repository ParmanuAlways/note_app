"""Extraction pipeline (FR-8..FR-11): original file -> page images -> VLM ->
validation -> a versioned Extraction row (FR-14a). Re-running never overwrites;
it adds a new version.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Document, Extraction
from app.inference.base import ExtractionClient
from app.services import audit, pdf_render
from app.services.extraction_schema import EXTRACTION_SCHEMA
from app.services.validation import validate


async def run_extraction(db: Session, owner_id: str, document: Document, client: ExtractionClient) -> Extraction:
    data = Path(document.storage_path).read_bytes()
    images = pdf_render.render_pages(data, document.filename)  # all pages (FR-8)

    result = await client.extract(images, EXTRACTION_SCHEMA)
    validated = validate(result.fields, datetime.now())  # FR-11

    # Full text retained for search (FR-9); reference number drives auto-link.
    document.full_text = result.full_text
    ref = validated.get("reference_number", {}).get("value")
    if ref:
        document.reference_number = ref

    # Next version for this document (FR-14a) — previous extractions are kept.
    current_max = db.scalar(
        select(func.max(Extraction.version)).where(Extraction.document_id == document.id)
    )
    version = (current_max or 0) + 1

    ext = Extraction(
        owner_id=owner_id,
        document_id=document.id,
        version=version,
        fields=validated,
        model_used=get_settings().extraction.model,
        confirmed=False,
    )
    db.add(ext)
    db.flush()
    audit.record(
        db, owner_id=owner_id, item_type="document", item_id=document.id,
        action="extracted", detail={"extraction_id": ext.id, "version": version},
    )
    db.commit()
    db.refresh(ext)
    return ext
