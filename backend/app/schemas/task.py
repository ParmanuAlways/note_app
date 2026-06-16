"""Task API schemas. Transport is ISO-8601; DD MMM YYYY is display-only (NFR-5)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import TaskStatus


class TaskCreate(BaseModel):
    title: str
    due_at: datetime | None = None
    reply_by: datetime | None = None  # suspense / reply-by date (FR-23)


class TaskUpdate(BaseModel):
    title: str | None = None
    status: TaskStatus | None = None  # open <-> done (FR-22)
    due_at: datetime | None = None
    reply_by: datetime | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    status: TaskStatus
    due_at: datetime | None
    reply_by: datetime | None
    source_document_id: str | None
    source_note_id: str | None


class SuspenseItem(TaskRead):
    """A reply-by task plus whether it is overdue (FR-23)."""

    overdue: bool
