"""The extraction contract (FR-8/9/10).

Defines the exact fields the VLM must return and the JSON Schema used for
guided decoding, so the model's output is always structurally valid. Dates are
demanded in ISO (YYYY-MM-DD) so the validation layer can parse them
deterministically; the model also returns the verbatim source text + page for
each field, which powers the confirm screen (FR-14).
"""

from __future__ import annotations

# Date-typed fields get the strict ISO + past/overdue rules in validation.py.
DATE_FIELDS = {"meeting_date", "reply_by_date"}

# Human-facing field order for the confirm screen.
FIELDS = [
    "subject",
    "meeting_date",
    "meeting_time",
    "venue",
    "attendees",
    "reference_number",
    "deadline_action",
    "reply_by_date",
]

_field = {
    "type": "object",
    "properties": {
        # null (not a guess) when the field is absent (FR-11: never invented).
        "value": {"type": ["string", "null"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "source_text": {"type": ["string", "null"]},  # verbatim, for verification
        "page": {"type": ["integer", "null"]},
    },
    "required": ["value", "confidence"],
}

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        **{name: _field for name in FIELDS},
        # Complete text the model read, retained for full-text search (FR-9).
        "full_text": {"type": "string"},
    },
    "required": [*FIELDS, "full_text"],
}

PROMPT = (
    "You are reading an official letter. Extract ONLY what is written; never "
    "guess. For any field not present, set value to null. Dates MUST be "
    "returned as ISO YYYY-MM-DD exactly as written in the document. For each "
    "field also return the verbatim source_text you read it from and its page "
    "number. Return the complete text you read in full_text. Give a calibrated "
    "confidence in [0,1] per field."
)
