"""Document extraction via Ollama (CPU-capable, for GPU-free dev on this box).

Ollama is OpenAI-ish but enforces structured output through its own `format`
field (a JSON Schema) on /api/chat, and takes page images as base64 strings —
so it gets its own small adapter rather than reusing the vLLM client. Selected
via INFERENCE_EXTRACTION_ENGINE=ollama. No app code outside the factory knows
it exists (NFR-7).
"""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from app.config import ExtractionConfig
from app.inference.base import ExtractionClient, ExtractionResult, InferenceUnavailable
from app.services.extraction_schema import PROMPT


class OllamaVisionExtractionClient(ExtractionClient):
    def __init__(self, cfg: ExtractionConfig) -> None:
        self._cfg = cfg
        self._base = cfg.base_url.rstrip("/")

    async def extract(self, images: list[bytes], json_schema: dict[str, Any]) -> ExtractionResult:
        body = {
            "model": self._cfg.model,
            "messages": [
                {
                    "role": "user",
                    "content": PROMPT,
                    "images": [base64.b64encode(img).decode() for img in images],
                }
            ],
            "format": json_schema,   # constrained decoding to our schema (FR-10)
            "stream": False,
            # A page image (~1.3k tokens) + the schema overflow the 4k default;
            # widen the window so multi-page letters fit (FR-8).
            "options": {"temperature": 0, "num_ctx": 16384},
        }
        try:
            # CPU inference is slow — generous timeout (NFR-1: accuracy > latency).
            async with httpx.AsyncClient(timeout=600.0) as client:
                resp = await client.post(f"{self._base}/api/chat", json=body)
                resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise InferenceUnavailable(f"ollama extraction error: {exc}") from exc

        data = json.loads(resp.json()["message"]["content"] or "{}")
        full_text = data.pop("full_text", "")
        fields = {k: v for k, v in data.items() if isinstance(v, dict)}
        return ExtractionResult(fields=fields, full_text=full_text)

    async def healthy(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                await client.get(f"{self._base}/api/tags")
            return True
        except Exception:  # noqa: BLE001
            return False
