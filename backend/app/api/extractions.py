"""Extraction API — trigger extraction on a stored document, fetch results and
their versions. The confirm step (creating an event/task from a result) is the
next slice.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner
from app.db.database import get_db
from app.db.models import Document, Extraction
from app.inference.base import InferenceUnavailable
from app.schemas.extraction import ExtractionRead
from app.services.extraction import run_extraction

router = APIRouter(tags=["extractions"])


def _get_document(db: Session, owner_id: str, doc_id: str) -> Document:
    doc = db.get(Document, doc_id)
    if doc is None or doc.owner_id != owner_id or doc.deleted_at is not None:
        raise HTTPException(404, "document not found")
    return doc


@router.post("/documents/{doc_id}/extract", response_model=ExtractionRead)
async def extract_document(
    doc_id: str,
    request: Request,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> Extraction:
    doc = _get_document(db, owner_id, doc_id)
    client = request.app.state.extraction_client
    if client is None:
        # Degraded mode (NFR-9): inference is off. The document is safe and
        # stored; queue-and-retry is a later refinement.
        raise HTTPException(503, "extraction inference is disabled")
    try:
        return await run_extraction(db, owner_id, doc, client)
    except InferenceUnavailable as exc:
        raise HTTPException(503, f"extraction backend unavailable: {exc}")


@router.get("/documents/{doc_id}/extractions", response_model=list[ExtractionRead])
def list_extractions(
    doc_id: str,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> list[Extraction]:
    _get_document(db, owner_id, doc_id)
    stmt = select(Extraction).where(Extraction.document_id == doc_id).order_by(Extraction.version.desc())
    return list(db.scalars(stmt))


@router.get("/extractions/{extraction_id}", response_model=ExtractionRead)
def get_extraction(
    extraction_id: str,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> Extraction:
    ext = db.get(Extraction, extraction_id)
    if ext is None or ext.owner_id != owner_id:
        raise HTTPException(404, "extraction not found")
    return ext
