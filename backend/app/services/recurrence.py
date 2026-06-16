"""RRULE expansion (FR-20). Turns a stored recurrence rule into concrete
occurrences within a date window, skipping excluded/overridden dates.

We use python-dateutil (RFC 5545) rather than hand-rolling date math (NFR-8
spirit). A recurring series is stored once as a master Event with an `rrule`;
occurrences are computed on read, never materialised as rows — except when a
single occurrence is overridden, which splits off a detached child event.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from dateutil.rrule import rrulestr

from app.db.models import Event

# How far to expand an unbounded series when the caller gives no upper bound.
_DEFAULT_HORIZON = timedelta(days=366)


def occurrences_in_range(
    ev: Event, range_start: datetime | None, range_end: datetime | None
) -> list[dict[str, Any]]:
    duration = (ev.ends_at - ev.starts_at) if ev.ends_at else None
    exdates = set(ev.exdates or [])

    if ev.rrule:
        rule = rrulestr(f"RRULE:{ev.rrule}", dtstart=ev.starts_at)
        lo = range_start or ev.starts_at
        hi = range_end or (lo + _DEFAULT_HORIZON)
        starts = list(rule.between(lo, hi, inc=True))
    else:
        starts = [ev.starts_at]

    out: list[dict[str, Any]] = []
    for s in starts:
        if s.isoformat() in exdates:
            continue
        if range_start and s < range_start:
            continue
        if range_end and s >= range_end:
            continue
        out.append(
            {
                "event_id": ev.id,
                "title": ev.title,
                "occurrence_start": s,
                "occurrence_end": (s + duration) if duration else None,
                "venue": ev.venue,
                "attendees": ev.attendees,
                "classification": ev.classification,
                "rrule": ev.rrule,
                "is_recurring": bool(ev.rrule),
                "is_override": ev.recurrence_parent_id is not None,
            }
        )
    return out
