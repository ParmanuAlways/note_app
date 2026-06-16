"""Document API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    mime_type: str
    page_count: int
    content_hash: str
    reference_number: str | None
    classification: str | None
    created_at: datetime


class UploadItem(BaseModel):
    """Per-file outcome in a batch (FR-2): the queue is visible, not guessed."""

    filename: str
    status: str  # uploaded | duplicate | rejected
    reason: str | None = None
    document_id: str | None = None
    duplicate_of: str | None = None  # existing doc id when status == duplicate


class UploadResponse(BaseModel):
    items: list[UploadItem]
