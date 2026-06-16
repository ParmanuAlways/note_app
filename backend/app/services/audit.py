"""Audit trail helper (FR-28). Every state change calls this so any item can
show its history in order. The caller commits."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLog


def record(
    db: Session,
    *,
    owner_id: str,
    item_type: str,
    item_id: str,
    action: str,
    detail: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            owner_id=owner_id,
            item_type=item_type,
            item_id=item_id,
            action=action,
            detail=detail,
        )
    )
