"""Note API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import CaptureSource


class NoteCreate(BaseModel):
    title: str
    content: str = ""
    classification: str | None = None


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    classification: str | None = None


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    source: CaptureSource
    classification: str | None
    audio_path: str | None
    created_at: datetime
    updated_at: datetime
    content: str = ""  # filled from the git-backed file, not the DB row


class NoteVersion(BaseModel):
    sha: str
    message: str
    at: datetime
