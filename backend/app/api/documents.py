"""Documents API — intake of scanned letters (FR-1/2/3) + original retention
(FR-27). AI-free: this is just capture/storage/dedup; the VLM reads them in
Phase 2.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner
from app.config import get_settings
from app.db.database import get_db
from app.db.models import AuditLog, Document
from app.schemas.document import DocumentRead, UploadItem, UploadResponse
from app.services import audit, storage

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_owned(db: Session, owner_id: str, doc_id: str, *, include_trashed: bool = False) -> Document:
    doc = db.get(Document, doc_id)
    if doc is None or doc.owner_id != owner_id:
        raise HTTPException(404, "document not found")
    if doc.deleted_at is not None and not include_trashed:
        raise HTTPException(404, "document is in trash")
    return doc


@router.post("", response_model=UploadResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    force: bool = Query(False, description="store even if a duplicate is detected (FR-3)"),
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> UploadResponse:
    settings = get_settings()
    if len(files) > settings.max_batch_files:
        # Whole-batch limit stated up front, never discovered by crash (FR-1).
        raise HTTPException(413, f"too many files: max {settings.max_batch_files} per batch")
    max_bytes = settings.max_file_mb * 1024 * 1024

    items: list[UploadItem] = []
    for f in files:
        data = await f.read()

        if not storage.is_accepted(f.filename or "", f.content_type):
            items.append(UploadItem(filename=f.filename or "", status="rejected",
                                    reason="unsupported file type (allowed: PDF, JPG, PNG, TIFF)"))
            continue
        if len(data) > max_bytes:
            items.append(UploadItem(filename=f.filename or "", status="rejected",
                                    reason=f"exceeds {settings.max_file_mb} MB limit"))
            continue

        # Stage-1 dedup: identical bytes already stored? (FR-3) Prompt, don't
        # silently copy — unless the user explicitly chose to proceed.
        h = storage.content_hash(data)
        existing = db.scalar(
            select(Document).where(
                Document.owner_id == owner_id,
                Document.content_hash == h,
                Document.deleted_at.is_(None),
            )
        )
        if existing and not force:
            items.append(UploadItem(filename=f.filename or "", status="duplicate",
                                    duplicate_of=existing.id))
            continue

        doc = Document(
            owner_id=owner_id,
            filename=f.filename or "upload",
            content_hash=h,
            mime_type=f.content_type or "application/octet-stream",
            page_count=storage.page_count(data, f.filename or ""),
            storage_path="",
        )
        db.add(doc)
        db.flush()
        doc.storage_path = storage.save(owner_id, doc.id, f.filename or "upload", data)
        audit.record(db, owner_id=owner_id, item_type="document", item_id=doc.id,
                     action="uploaded", detail={"pages": doc.page_count, "forced": force})
        items.append(UploadItem(filename=doc.filename, status="uploaded", document_id=doc.id))

    db.commit()
    return UploadResponse(items=items)


@router.get("", response_model=list[DocumentRead])
def list_documents(db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> list[Document]:
    stmt = select(Document).where(
        Document.owner_id == owner_id, Document.deleted_at.is_(None)
    ).order_by(Document.created_at.desc())
    return list(db.scalars(stmt))


@router.get("/{doc_id}", response_model=DocumentRead)
def get_document(doc_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> Document:
    return _get_owned(db, owner_id, doc_id)


@router.get("/{doc_id}/file")
def download_original(doc_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> FileResponse:
    # The original is openable from any linked note/event (FR-27).
    doc = _get_owned(db, owner_id, doc_id)
    return FileResponse(doc.storage_path, media_type=doc.mime_type, filename=doc.filename)


@router.delete("/{doc_id}", status_code=204, response_class=Response)
def delete_document(doc_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> Response:
    doc = _get_owned(db, owner_id, doc_id)
    doc.deleted_at = datetime.now()
    audit.record(db, owner_id=owner_id, item_type="document", item_id=doc.id, action="deleted")
    db.commit()
    return Response(status_code=204)


@router.post("/{doc_id}/restore", response_model=DocumentRead)
def restore_document(doc_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> Document:
    doc = _get_owned(db, owner_id, doc_id, include_trashed=True)
    if doc.deleted_at is None:
        raise HTTPException(400, "document is not in trash")
    doc.deleted_at = None
    audit.record(db, owner_id=owner_id, item_type="document", item_id=doc.id, action="restored")
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{doc_id}/history")
def document_history(doc_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> list[dict]:
    _get_owned(db, owner_id, doc_id, include_trashed=True)
    stmt = select(AuditLog).where(
        AuditLog.owner_id == owner_id, AuditLog.item_type == "document", AuditLog.item_id == doc_id
    ).order_by(AuditLog.at)
    return [{"at": a.at, "action": a.action, "detail": a.detail} for a in db.scalars(stmt)]
