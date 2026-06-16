"""Event API schemas.

Transport is ISO-8601 (machine format). The DD MMM YYYY convention (NFR-5) is
applied at *display* time in the frontend — never store or transport US MM/DD.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventCreate(BaseModel):
    title: str
    starts_at: datetime
    ends_at: datetime | None = None
    venue: str | None = None
    attendees: str | None = None
    rrule: str | None = None
    classification: str | None = None


class EventUpdate(BaseModel):
    """All optional — supports edit and reschedule (FR-18)."""

    title: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    venue: str | None = None
    attendees: str | None = None
    rrule: str | None = None
    classification: str | None = None


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    starts_at: datetime
    ends_at: datetime | None
    venue: str | None
    attendees: str | None
    rrule: str | None
    classification: str | None
    source_document_id: str | None
    source_note_id: str | None
