"""Mock extraction client — lets the whole pipeline run and be tested without a
GPU/VLM. Selected via INFERENCE_EXTRACTION_ENGINE=mock. Returns a deterministic
result resembling a multi-page letter (reply-by on a later page, FR-8).
"""

from __future__ import annotations

from typing import Any

from app.config import ExtractionConfig
from app.inference.base import ExtractionClient, ExtractionResult


class MockExtractionClient(ExtractionClient):
    def __init__(self, cfg: ExtractionConfig) -> None:
        self._cfg = cfg

    async def extract(self, images: list[bytes], json_schema: dict[str, Any]) -> ExtractionResult:
        pages = len(images)
        fields = {
            "subject": {"value": "Coordination Conference – Q3 Planning", "confidence": 0.96, "source_text": "Subject: Coordination Conference", "page": 1},
            "meeting_date": {"value": "2026-07-15", "confidence": 0.74, "source_text": "on 15 Jul 2026", "page": 1},
            "meeting_time": {"value": "10:30", "confidence": 0.62, "source_text": "at 1030 hrs", "page": 1},
            "venue": {"value": "Conference Hall, Block C", "confidence": 0.88, "source_text": "venue: Conference Hall, Block C", "page": 1},
            "attendees": {"value": "Maj Rao, Capt Iyer", "confidence": 0.7, "source_text": "all section heads", "page": 1},
            "reference_number": {"value": "HQ/PLN/2026/0457", "confidence": 0.99, "source_text": "Ref: HQ/PLN/2026/0457", "page": 1},
            "deadline_action": {"value": "Submit unit inputs", "confidence": 0.8, "source_text": "submit inputs", "page": pages},
            # A reply-by in the past -> validation should mark it overdue.
            "reply_by_date": {"value": "2026-06-10", "confidence": 0.83, "source_text": "reply by 10 Jun 2026", "page": pages},
        }
        full_text = f"[mock extraction of a {pages}-page document] Ref HQ/PLN/2026/0457 ..."
        return ExtractionResult(fields=fields, full_text=full_text)

    async def healthy(self) -> bool:
        return True
