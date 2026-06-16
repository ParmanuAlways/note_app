"""Abstract inference interfaces — the swappable layer (NFR-7).

The rest of the application depends ONLY on these abstract classes, never on a
concrete model, vendor, or server. A model/hardware swap is wired entirely
through `factory.py` + config. If a backend is disabled or unreachable, the
client raises `InferenceUnavailable`; callers degrade gracefully (NFR-9).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


class InferenceUnavailable(RuntimeError):
    """Raised when an inference backend is disabled or cannot be reached.

    Callers must catch this and fall back to degraded mode (NFR-9): queue the
    work for retry, never crash the request.
    """


@dataclass
class ExtractionField:
    """One extracted value plus its self-reported confidence (FR-10).

    NOTE: VLMs do not produce calibrated confidence. `confidence` is a
    review hint only; the confirm step (FR-14) is the real safety net.
    """

    value: Any
    confidence: float


@dataclass
class ExtractionResult:
    fields: dict[str, ExtractionField]
    full_text: str  # complete text the model read, for search (FR-9)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TranscriptSegment:
    text: str
    start: float
    end: float
    is_final: bool


class ExtractionClient(abc.ABC):
    """Vision-language document extraction (FR-8..FR-11)."""

    @abc.abstractmethod
    async def extract(
        self, images: list[bytes], json_schema: dict[str, Any]
    ) -> ExtractionResult:
        """Read document page images, return structured fields constrained to
        `json_schema` (guided decoding) plus the full read-back text."""

    @abc.abstractmethod
    async def healthy(self) -> bool: ...


class TranscriptionClient(abc.ABC):
    """Local speech-to-text (FR-6). Supports streaming and full-file passes."""

    @abc.abstractmethod
    def stream(self) -> "AsyncIterator[TranscriptSegment]":
        """Live partial transcript while recording (UX feedback)."""

    @abc.abstractmethod
    async def transcribe_file(self, audio: bytes) -> str:
        """Authoritative full-file transcript saved to the record."""

    @abc.abstractmethod
    async def healthy(self) -> bool: ...


class EmbeddingClient(abc.ABC):
    """Local text embeddings for semantic search (FR-25, FR-31)."""

    @abc.abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    @property
    @abc.abstractmethod
    def dim(self) -> int: ...

    @abc.abstractmethod
    async def healthy(self) -> bool: ...
