"""Core schema (v1).

Every user-owned row carries `owner_id` AND `unit_id` from day one. v1 is
single-user, but these fields mean v2 (shared unit workspace) is an extension,
not a rewrite (requirements §2.5, §6 v2). Nothing here is wired to access
control yet — the classification tag is findability only in v1 (FR-36, §7.1).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class OwnerMixin:
    """Per-user keying for v1; the seam for v2 multi-user."""

    owner_id: Mapped[str] = mapped_column(String, index=True)
    unit_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # Soft delete -> trash (FR-19). A non-null value means "in trash".
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CaptureSource(str, enum.Enum):
    document = "document"
    typed = "typed"
    voice = "voice"
    manual = "manual"  # FR-7, no AI


class TaskStatus(str, enum.Enum):
    open = "open"
    done = "done"


class Document(Base, OwnerMixin, TimestampMixin):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String)
    content_hash: Mapped[str] = mapped_column(String, index=True)  # dedup stage 1 (FR-3)
    storage_path: Mapped[str] = mapped_column(String)  # original retained (FR-27)
    mime_type: Mapped[str] = mapped_column(String)
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # FR-9 search
    reference_number: Mapped[str | None] = mapped_column(String, index=True, nullable=True)  # FR-24
    classification: Mapped[str | None] = mapped_column(String, nullable=True)  # FR-36

    extractions: Mapped[list["Extraction"]] = relationship(back_populates="document")


class Extraction(Base, OwnerMixin, TimestampMixin):
    """Versioned extraction output — re-extraction never overwrites (FR-14a)."""

    __tablename__ = "extractions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    fields: Mapped[dict] = mapped_column(JSON)  # {field: {value, confidence}} (FR-10)
    model_used: Mapped[str] = mapped_column(String)  # provenance for swap audits
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)  # FR-14

    document: Mapped[Document] = relationship(back_populates="extractions")


class Note(Base, OwnerMixin, TimestampMixin):
    """Markdown stored on disk + git history (FR-38/39); row is the index."""

    __tablename__ = "notes"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String)
    storage_path: Mapped[str] = mapped_column(String)  # path to .md in per-user git repo
    source: Mapped[CaptureSource] = mapped_column(Enum(CaptureSource), default=CaptureSource.typed)
    audio_path: Mapped[str | None] = mapped_column(String, nullable=True)  # FR-6 retained audio
    classification: Mapped[str | None] = mapped_column(String, nullable=True)


class Event(Base, OwnerMixin, TimestampMixin):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    venue: Mapped[str | None] = mapped_column(String, nullable=True)
    attendees: Mapped[str | None] = mapped_column(Text, nullable=True)  # text metadata only (FR-17)
    rrule: Mapped[str | None] = mapped_column(String, nullable=True)  # RFC 5545 recurrence (FR-20)
    classification: Mapped[str | None] = mapped_column(String, nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    source_note_id: Mapped[str | None] = mapped_column(ForeignKey("notes.id"), nullable=True)


class Task(Base, OwnerMixin, TimestampMixin):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.open)  # FR-22
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Suspense / reply-by (FR-23). Past reply-by is valid + overdue, not rejected (FR-11).
    reply_by: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    source_note_id: Mapped[str | None] = mapped_column(ForeignKey("notes.id"), nullable=True)


class ItemLink(Base, OwnerMixin, TimestampMixin):
    """Hard auto-links (FR-24) and confirmed soft suggestions (FR-25)."""

    __tablename__ = "item_links"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    from_type: Mapped[str] = mapped_column(String)
    from_id: Mapped[str] = mapped_column(String, index=True)
    to_type: Mapped[str] = mapped_column(String)
    to_id: Mapped[str] = mapped_column(String, index=True)
    link_kind: Mapped[str] = mapped_column(String)  # "hard_reference" | "soft_semantic"


class AuditLog(Base, OwnerMixin):
    """Append-only trail, viewable per item (FR-28)."""

    __tablename__ = "audit_log"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    item_type: Mapped[str] = mapped_column(String, index=True)
    item_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)  # uploaded|extracted|edited|created|...
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
