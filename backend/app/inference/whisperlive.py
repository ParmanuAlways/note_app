"""Streaming voice transcription via WhisperLive (faster-whisper backend).

Phase 0 ships the interface + health check. The live WebSocket bridge and the
authoritative full-file pass are implemented in Phase 3 (FR-6).
"""

from __future__ import annotations

from typing import AsyncIterator

import httpx

from app.config import TranscriptionConfig
from app.inference.base import (
    InferenceUnavailable,
    TranscriptionClient,
    TranscriptSegment,
)


class WhisperLiveTranscriptionClient(TranscriptionClient):
    def __init__(self, cfg: TranscriptionConfig) -> None:
        self._cfg = cfg

    async def stream(self) -> AsyncIterator[TranscriptSegment]:  # pragma: no cover
        # Implemented in Phase 3: browser mic -> WebSocket -> live partials.
        raise NotImplementedError("streaming transcription lands in Phase 3")
        yield  # pragma: no cover  (makes this an async generator)

    async def transcribe_file(self, audio: bytes) -> str:  # pragma: no cover
        raise NotImplementedError("full-file transcription lands in Phase 3")

    async def healthy(self) -> bool:
        # WhisperLive exposes a WS port; a TCP/HTTP probe confirms reachability.
        host = self._cfg.ws_url.replace("ws://", "http://").replace("wss://", "https://")
        try:
            async with httpx.AsyncClient(timeout=2.0) as c:
                await c.get(host)
            return True
        except httpx.HTTPStatusError:
            return True  # reachable, just not an HTTP route
        except Exception as exc:  # noqa: BLE001
            raise InferenceUnavailable(str(exc)) from exc
