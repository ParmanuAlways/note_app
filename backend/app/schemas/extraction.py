"""Extraction API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ExtractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    version: int
    fields: dict[str, Any]  # {field: {value, confidence, source_text, page, flags}}
    model_used: str
    confirmed: bool
    created_at: datetime


class ConfirmEvent(BaseModel):
    title: str
    starts_at: datetime
    ends_at: datetime | None = None
    venue: str | None = None
    attendees: str | None = None
    classification: str | None = None


class ConfirmTask(BaseModel):
    title: str
    due_at: datetime | None = None
    reply_by: datetime | None = None


class ConfirmRequest(BaseModel):
    """The user's decision at the confirm screen (FR-14).

    create=event|task turns the (edited) extraction into a calendar item linked
    to its source; create=none dismisses the proposal but keeps the document.
    edited_fields carries any value the user corrected, for the audit trail.
    """

    create: Literal["event", "task", "none"]
    event: ConfirmEvent | None = None
    task: ConfirmTask | None = None
    edited_fields: dict[str, Any] | None = None


class ConfirmResponse(BaseModel):
    confirmed: bool
    created_type: str | None = None  # "event" | "task" | None
    created_id: str | None = None
