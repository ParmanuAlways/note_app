"""Extraction API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

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
