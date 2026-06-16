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
from app.db.models import Document, Event, Extraction, Task
from app.inference.base import InferenceUnavailable
from app.schemas.extraction import ConfirmRequest, ConfirmResponse, ExtractionRead
from app.services import audit
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


@router.post("/extractions/{extraction_id}/confirm", response_model=ConfirmResponse)
def confirm_extraction(
    extraction_id: str,
    payload: ConfirmRequest,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> ConfirmResponse:
    # The confirm step (FR-14): nothing reaches the calendar until the user
    # approves here. Dismiss (create=none) keeps the document, discards only
    # the proposed item.
    ext = db.get(Extraction, extraction_id)
    if ext is None or ext.owner_id != owner_id:
        raise HTTPException(404, "extraction not found")

    if payload.edited_fields:
        # Record the user's corrections back onto the extraction + audit them.
        fields = {k: dict(v) for k, v in ext.fields.items()}
        for key, value in payload.edited_fields.items():
            if key in fields:
                fields[key]["value"] = value
        ext.fields = fields
        audit.record(db, owner_id=owner_id, item_type="document", item_id=ext.document_id,
                     action="extraction_edited", detail={"fields": sorted(payload.edited_fields)})

    ext.confirmed = True
    created_type: str | None = None
    created_id: str | None = None

    if payload.create == "event":
        if payload.event is None:
            raise HTTPException(400, "event details required when create=event")
        ev = Event(owner_id=owner_id, source_document_id=ext.document_id, **payload.event.model_dump())
        db.add(ev)
        db.flush()
        audit.record(db, owner_id=owner_id, item_type="event", item_id=ev.id,
                     action="created", detail={"source": "extraction", "document_id": ext.document_id})
        created_type, created_id = "event", ev.id
    elif payload.create == "task":
        if payload.task is None:
            raise HTTPException(400, "task details required when create=task")
        tk = Task(owner_id=owner_id, source_document_id=ext.document_id, **payload.task.model_dump())
        db.add(tk)
        db.flush()
        audit.record(db, owner_id=owner_id, item_type="task", item_id=tk.id,
                     action="created", detail={"source": "extraction", "document_id": ext.document_id})
        created_type, created_id = "task", tk.id

    audit.record(db, owner_id=owner_id, item_type="document", item_id=ext.document_id,
                 action="confirmed", detail={"created": created_type})
    db.commit()
    return ConfirmResponse(confirmed=True, created_type=created_type, created_id=created_id)
