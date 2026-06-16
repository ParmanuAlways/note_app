"""Notes API — typed notes (FR-5) stored as markdown with git history
(FR-38/39). AI-free backbone (NFR-9)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner
from app.db.database import get_db
from app.db.models import AuditLog, Note
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate, NoteVersion
from app.services import audit, notes_repo

router = APIRouter(prefix="/notes", tags=["notes"])


def _get_owned(db: Session, owner_id: str, note_id: str, *, include_trashed: bool = False) -> Note:
    n = db.get(Note, note_id)
    if n is None or n.owner_id != owner_id:
        raise HTTPException(404, "note not found")
    if n.deleted_at is not None and not include_trashed:
        raise HTTPException(404, "note is in trash")
    return n


def _with_content(note: Note, content: str) -> NoteRead:
    out = NoteRead.model_validate(note, from_attributes=True)
    out.content = content
    return out


@router.post("", response_model=NoteRead, status_code=201)
def create_note(payload: NoteCreate, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> NoteRead:
    note = Note(owner_id=owner_id, title=payload.title, classification=payload.classification, storage_path="")
    db.add(note)
    db.flush()  # need note.id for the file name
    note.storage_path = notes_repo.write(owner_id, note.id, payload.content, f"create: {payload.title}")
    audit.record(db, owner_id=owner_id, item_type="note", item_id=note.id, action="created")
    db.commit()
    db.refresh(note)
    return _with_content(note, payload.content)


@router.get("", response_model=list[NoteRead])
def list_notes(db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> list[NoteRead]:
    # Metadata only (content left empty) to avoid reading every file on a list.
    stmt = select(Note).where(Note.owner_id == owner_id, Note.deleted_at.is_(None)).order_by(Note.updated_at.desc())
    return [NoteRead.model_validate(n, from_attributes=True) for n in db.scalars(stmt)]


@router.get("/{note_id}", response_model=NoteRead)
def get_note(note_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> NoteRead:
    note = _get_owned(db, owner_id, note_id)
    return _with_content(note, notes_repo.read(owner_id, note_id))


@router.patch("/{note_id}", response_model=NoteRead)
def update_note(note_id: str, payload: NoteUpdate, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> NoteRead:
    note = _get_owned(db, owner_id, note_id)
    changes = payload.model_dump(exclude_unset=True)
    if "title" in changes:
        note.title = changes["title"]
    if "classification" in changes:
        note.classification = changes["classification"]
    content = notes_repo.read(owner_id, note_id)
    if "content" in changes and changes["content"] != content:
        # Every edit is a commit -> version history (FR-39).
        content = changes["content"]
        notes_repo.write(owner_id, note_id, content, f"edit: {note.title}")
    audit.record(db, owner_id=owner_id, item_type="note", item_id=note.id, action="edited",
                 detail={"fields": sorted(changes.keys())})
    db.commit()
    db.refresh(note)
    return _with_content(note, content)


@router.get("/{note_id}/versions", response_model=list[NoteVersion])
def note_versions(note_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> list[dict]:
    _get_owned(db, owner_id, note_id, include_trashed=True)
    return notes_repo.versions(owner_id, note_id)


@router.get("/{note_id}/versions/{sha}")
def note_version_content(note_id: str, sha: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> dict:
    _get_owned(db, owner_id, note_id, include_trashed=True)
    try:
        return {"sha": sha, "content": notes_repo.read_version(owner_id, note_id, sha)}
    except KeyError:
        raise HTTPException(404, "version not found")


@router.delete("/{note_id}", status_code=204, response_class=Response)
def delete_note(note_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> Response:
    note = _get_owned(db, owner_id, note_id)
    note.deleted_at = datetime.now()
    audit.record(db, owner_id=owner_id, item_type="note", item_id=note.id, action="deleted")
    db.commit()
    return Response(status_code=204)


@router.post("/{note_id}/restore", response_model=NoteRead)
def restore_note(note_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> NoteRead:
    note = _get_owned(db, owner_id, note_id, include_trashed=True)
    if note.deleted_at is None:
        raise HTTPException(400, "note is not in trash")
    note.deleted_at = None
    audit.record(db, owner_id=owner_id, item_type="note", item_id=note.id, action="restored")
    db.commit()
    db.refresh(note)
    return _with_content(note, notes_repo.read(owner_id, note_id))


@router.get("/{note_id}/history")
def note_history(note_id: str, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> list[dict]:
    _get_owned(db, owner_id, note_id, include_trashed=True)
    stmt = select(AuditLog).where(
        AuditLog.owner_id == owner_id, AuditLog.item_type == "note", AuditLog.item_id == note_id
    ).order_by(AuditLog.at)
    return [{"at": a.at, "action": a.action, "detail": a.detail} for a in db.scalars(stmt)]
