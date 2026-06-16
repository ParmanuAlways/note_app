"""Events API — manual entry path (FR-7) + lifecycle (FR-18/19) + audit (FR-28).

This is the AI-free backbone: it works with no GPU and no models (NFR-9).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_owner
from app.db.database import get_db
from app.db.models import AuditLog, Event
from app.schemas.event import EventCreate, EventRead, EventUpdate, OccurrenceRead
from app.services import audit
from app.services.recurrence import occurrences_in_range

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


@router.get("", response_model=list[OccurrenceRead])
def list_events(
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
    start: datetime | None = Query(None, description="range start (inclusive)"),
    end: datetime | None = Query(None, description="range end (exclusive)"),
) -> list[dict]:
    # Recurring masters are expanded on read (FR-20), so we can't filter by
    # starts_at in SQL — a weekly series starting in January still has
    # occurrences in June. Fetch all, expand each within the window.
    stmt = select(Event).where(Event.owner_id == owner_id, Event.deleted_at.is_(None))
    occ: list[dict] = []
    for ev in db.scalars(stmt):
        occ.extend(occurrences_in_range(ev, start, end))
    occ.sort(key=lambda o: o["occurrence_start"])
    return occ


@router.get("/trash", response_model=list[EventRead])
def list_trash(
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> list[Event]:
    stmt = select(Event).where(
        Event.owner_id == owner_id, Event.deleted_at.is_not(None)
    ).order_by(Event.deleted_at.desc())
    return list(db.scalars(stmt))


@router.get("/conflicts", response_model=list[OccurrenceRead])
def conflicts(
    start: datetime,
    end: datetime | None = None,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
) -> list[dict]:
    # Overlap check for the confirm screen (FR-15). A missing end is treated as
    # a 1-hour block. Recurring events are expanded over the surrounding window
    # so a repeating occurrence on the proposed day is caught too.
    proposed_end = end or (start + timedelta(hours=1))
    win_lo, win_hi = start - timedelta(days=1), proposed_end + timedelta(days=1)
    clashes: list[dict] = []
    stmt = select(Event).where(Event.owner_id == owner_id, Event.deleted_at.is_(None))
    for ev in db.scalars(stmt):
        for occ in occurrences_in_range(ev, win_lo, win_hi):
            occ_start = occ["occurrence_start"]
            occ_end = occ["occurrence_end"] or (occ_start + timedelta(hours=1))
            if occ_start < proposed_end and occ_end > start:  # intervals overlap
                clashes.append(occ)
    return clashes


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
    scope: Literal["series", "occurrence"] = Query(
        "series", description="edit the whole series or just one occurrence"
    ),
    occurrence: datetime | None = Query(
        None, description="the occurrence start to override (scope=occurrence)"
    ),
) -> Event:
    ev = _get_owned(db, owner_id, event_id)
    changes = payload.model_dump(exclude_unset=True)

    if scope == "occurrence":
        # Split one instance off the series (FR-20): exclude it from the master
        # and create a standalone override carrying the edits.
        if occurrence is None:
            raise HTTPException(400, "occurrence is required when scope=occurrence")
        if not ev.rrule:
            raise HTTPException(400, "event is not recurring")
        ev.exdates = list(ev.exdates or []) + [occurrence.isoformat()]
        duration = (ev.ends_at - ev.starts_at) if ev.ends_at else None
        override = Event(
            owner_id=owner_id,
            title=changes.get("title", ev.title),
            starts_at=changes.get("starts_at", occurrence),
            ends_at=changes.get(
                "ends_at", (occurrence + duration) if duration else None
            ),
            venue=changes.get("venue", ev.venue),
            attendees=changes.get("attendees", ev.attendees),
            classification=changes.get("classification", ev.classification),
            rrule=None,
            recurrence_parent_id=ev.id,
        )
        db.add(override)
        db.flush()
        audit.record(
            db, owner_id=owner_id, item_type="event", item_id=ev.id,
            action="occurrence_edited",
            detail={"occurrence": occurrence.isoformat(), "override_id": override.id},
        )
        db.commit()
        db.refresh(override)
        return override

    rescheduled = "starts_at" in changes and changes["starts_at"] != ev.starts_at
    for field, value in changes.items():
        setattr(ev, field, value)
    audit.record(
        db, owner_id=owner_id, item_type="event", item_id=ev.id,
        action="rescheduled" if rescheduled else "edited",
        detail={"fields": sorted(changes.keys()), "scope": "series"},
    )
    db.commit()
    db.refresh(ev)
    return ev


@router.delete("/{event_id}", status_code=204, response_class=Response)
def delete_event(
    event_id: str,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner),
    scope: Literal["series", "occurrence"] = Query("series"),
    occurrence: datetime | None = Query(None),
) -> Response:
    ev = _get_owned(db, owner_id, event_id)

    if scope == "occurrence":
        # Remove a single instance from the series without touching the rest.
        if occurrence is None:
            raise HTTPException(400, "occurrence is required when scope=occurrence")
        if not ev.rrule:
            raise HTTPException(400, "event is not recurring")
        ev.exdates = list(ev.exdates or []) + [occurrence.isoformat()]
        audit.record(
            db, owner_id=owner_id, item_type="event", item_id=ev.id,
            action="occurrence_deleted", detail={"occurrence": occurrence.isoformat()},
        )
        db.commit()
        return Response(status_code=204)

    # Soft delete the whole series -> trash (FR-19). No hard delete from the UI.
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
