"""Unified trash view (FR-19). Lists soft-deleted items across all types so the
UI has one restore surface. Restore stays on each type's own endpoint.

Hard delete is deliberately absent — the only permanent-removal path is the
timed purge from trash (a Phase 5 background job). In a records context,
accidental permanent loss is unacceptable.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner
from app.db.database import get_db
from app.db.models import Document, Event, Note, Task

router = APIRouter(prefix="/trash", tags=["trash"])


@router.get("")
def list_trash(db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner)) -> list[dict]:
    items: list[dict] = []

    def collect(model, type_name: str, label):
        stmt = select(model).where(model.owner_id == owner_id, model.deleted_at.is_not(None))
        for row in db.scalars(stmt):
            items.append({
                "type": type_name,
                "id": row.id,
                "title": label(row),
                "deleted_at": row.deleted_at,
            })

    collect(Event, "event", lambda r: r.title)
    collect(Task, "task", lambda r: r.title)
    collect(Note, "note", lambda r: r.title)
    collect(Document, "document", lambda r: r.filename)

    items.sort(key=lambda i: i["deleted_at"], reverse=True)
    return items
