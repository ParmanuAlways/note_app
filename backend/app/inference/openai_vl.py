"""Document extraction via an OpenAI-compatible vision endpoint (e.g. vLLM
serving Qwen2.5-VL). The model identity comes from config — not hardcoded."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.config import ExtractionConfig
from app.inference.base import (
    ExtractionClient,
    ExtractionResult,
    InferenceUnavailable,
)


class OpenAIVisionExtractionClient(ExtractionClient):
    def __init__(self, cfg: ExtractionConfig) -> None:
        self._cfg = cfg
        self._client = AsyncOpenAI(base_url=cfg.base_url, api_key=cfg.api_key)

    async def extract(
        self, images: list[bytes], json_schema: dict[str, Any]
    ) -> ExtractionResult:
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "Read every page of this document. Extract the requested "
                    "fields exactly as written. Do NOT invent missing values — "
                    "leave a field null if it is not present. Also return the "
                    "complete text you read in `full_text`."
                ),
            }
        ]
        for img in images:
            b64 = base64.b64encode(img).decode()
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                }
            )

        try:
            resp = await self._client.chat.completions.create(
                model=self._cfg.model,
                messages=[{"role": "user", "content": content}],
                # Guided JSON decoding (FR-10): vLLM enforces the schema so the
                # output is always valid. Key passed via extra_body.
                extra_body={"guided_json": json_schema},
                temperature=0.0,
            )
        except (httpx.HTTPError, Exception) as exc:  # noqa: BLE001
            raise InferenceUnavailable(f"extraction backend error: {exc}") from exc

        data = json.loads(resp.choices[0].message.content or "{}")
        full_text = data.pop("full_text", "")
        # Guided decoding guarantees each field is {value, confidence,
        # source_text, page}; pass the dicts straight through to validation.
        fields = {k: v for k, v in data.items() if isinstance(v, dict)}
        return ExtractionResult(fields=fields, full_text=full_text)

    async def healthy(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:  # noqa: BLE001
            return False
