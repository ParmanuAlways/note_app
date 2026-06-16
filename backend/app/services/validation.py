"""Deterministic validation of extracted fields (FR-11) — the code half of the
date-accuracy defense (NFR-4). The model proposes; this layer checks. It never
invents a value; it only parses, sanity-checks, and flags for the confirm step.

Flags per field (shown/triggered on the confirm screen):
  missing          — model returned null
  low_confidence   — below the review threshold
  unreadable       — a date that isn't a real calendar date (left blank)
  implausible_past — a MEETING date in the past (kept, but flagged)
  overdue          — a REPLY-BY date in the past (valid — feeds suspense, FR-23)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.services.extraction_schema import DATE_FIELDS, FIELDS

LOW_CONFIDENCE = 0.6  # configurable later


def _parse_iso_date(value: str) -> date | None:
    """Strict: real calendar date only. '2026-02-30' -> None (unreadable)."""
    try:
        return datetime.fromisoformat(value).date() if "T" in value else date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def validate(extraction: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Return a per-field result: {value, confidence, source_text, page, flags}.

    Date fields are normalised to ISO; an unreadable date is blanked (never
    invented) and flagged. `now` is injectable for testing.
    """
    now = now or datetime.now()
    today = now.date()
    out: dict[str, Any] = {}

    for name in FIELDS:
        field = extraction.get(name) or {}
        value = field.get("value")
        confidence = float(field.get("confidence", 0.0))
        flags: list[str] = []

        if value in (None, ""):
            flags.append("missing")
        else:
            if confidence < LOW_CONFIDENCE:
                flags.append("low_confidence")
            if name in DATE_FIELDS:
                parsed = _parse_iso_date(str(value))
                if parsed is None:
                    value = None  # leave blank rather than store a bad date
                    flags.append("unreadable")
                else:
                    value = parsed.isoformat()
                    if name == "meeting_date" and parsed < today:
                        flags.append("implausible_past")
                    if name == "reply_by_date" and parsed < today:
                        flags.append("overdue")  # valid, not rejected (FR-11)

        out[name] = {
            "value": value,
            "confidence": confidence,
            "source_text": field.get("source_text"),
            "page": field.get("page"),
            "flags": flags,
        }

    return out
