"""Events API — manual entry path (FR-7) + lifecycle (FR-18/19) + audit (FR-28).

This is the AI-free backbone: it works with no GPU and no models (NFR-9).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner
from app.db.database import get_db
from app.db.models import AuditLog, Event
from app.schemas.event import EventCreate, EventRead, EventUpdate
from app.services import audit

router = APIRouter(prefix="/events", tags=["events"])


def _get_owned(db: Session, owner_id: str, event_id: str, *, include_trashed: bool = False) -> Event:
    ev = db.get(Event, event_id)
    if ev is None or ev.owner_id != owner_id:
        raise HTTPException(404, "event not found")
    if ev.deleted_at is not None and not include_trashed:
        raise HTTPException(404, "event is in trash")
    return ev


@router.post("", response_model=EventRead, status_code=201)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> Event:
    ev = Event(owner_id=owner_id, **payload.model_dump())
    db.add(ev)
    db.flush()  # assign id before auditing
    audit.record(
        db, owner_id=owner_id, item_type="event", item_id=ev.id,
        action="created", detail={"source": "manual"},
    )
    db.commit()
    db.refresh(ev)
    return ev


@router.get("", response_model=list[EventRead])
def list_events(
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
    start: datetime | None = Query(None, description="range start (inclusive)"),
    end: datetime | None = Query(None, description="range end (exclusive)"),
) -> list[Event]:
    stmt = select(Event).where(Event.owner_id == owner_id, Event.deleted_at.is_(None))
    if start is not None:
        stmt = stmt.where(Event.starts_at >= start)
    if end is not None:
        stmt = stmt.where(Event.starts_at < end)
    return list(db.scalars(stmt.order_by(Event.starts_at)))


@router.get("/trash", response_model=list[EventRead])
def list_trash(
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> list[Event]:
    stmt = select(Event).where(
        Event.owner_id == owner_id, Event.deleted_at.is_not(None)
    ).order_by(Event.deleted_at.desc())
    return list(db.scalars(stmt))


@router.get("/{event_id}", response_model=EventRead)
def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> Event:
    return _get_owned(db, owner_id, event_id)


@router.patch("/{event_id}", response_model=EventRead)
def update_event(
    event_id: str,
    payload: EventUpdate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> Event:
    ev = _get_owned(db, owner_id, event_id)
    changes = payload.model_dump(exclude_unset=True)
    rescheduled = "starts_at" in changes and changes["starts_at"] != ev.starts_at
    for field, value in changes.items():
        setattr(ev, field, value)
    audit.record(
        db, owner_id=owner_id, item_type="event", item_id=ev.id,
        action="rescheduled" if rescheduled else "edited",
        detail={"fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(ev)
    return ev


@router.delete("/{event_id}", status_code=204, response_class=Response)
def delete_event(
    event_id: str,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> Response:
    # Soft delete -> trash (FR-19). No hard delete from the UI.
    ev = _get_owned(db, owner_id, event_id)
    ev.deleted_at = datetime.now(tz=ev.starts_at.tzinfo)
    audit.record(db, owner_id=owner_id, item_type="event", item_id=ev.id, action="deleted")
    db.commit()
    return Response(status_code=204)


@router.post("/{event_id}/restore", response_model=EventRead)
def restore_event(
    event_id: str,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> Event:
    ev = _get_owned(db, owner_id, event_id, include_trashed=True)
    if ev.deleted_at is None:
        raise HTTPException(400, "event is not in trash")
    ev.deleted_at = None
    audit.record(db, owner_id=owner_id, item_type="event", item_id=ev.id, action="restored")
    db.commit()
    db.refresh(ev)
    return ev


@router.get("/{event_id}/history")
def event_history(
    event_id: str,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> list[dict]:
    # Per-item audit view (FR-28) — a log that can't be read satisfies nothing.
    _get_owned(db, owner_id, event_id, include_trashed=True)
    stmt = select(AuditLog).where(
        AuditLog.owner_id == owner_id,
        AuditLog.item_type == "event",
        AuditLog.item_id == event_id,
    ).order_by(AuditLog.at)
    return [
        {"at": a.at, "action": a.action, "detail": a.detail}
        for a in db.scalars(stmt)
    ]
