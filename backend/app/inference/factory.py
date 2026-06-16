"""Builds inference clients from config — the ONLY place concrete model
backends are selected (NFR-7). To support a new engine, add a branch here;
nothing else in the codebase changes.

Clients are returned as Optional: when a backend is disabled in config, the
factory returns None and callers run in degraded mode (NFR-9).
"""

from __future__ import annotations

from app.config import Settings
from app.inference.base import (
    EmbeddingClient,
    ExtractionClient,
    TranscriptionClient,
)
from app.inference.embeddings import OpenAIEmbeddingClient
from app.inference.openai_vl import OpenAIVisionExtractionClient
from app.inference.whisperlive import WhisperLiveTranscriptionClient


def build_extraction_client(settings: Settings) -> ExtractionClient | None:
    cfg = settings.extraction
    if not cfg.enabled:
        return None
    if cfg.engine == "mock":
        from app.inference.mock import MockExtractionClient

        return MockExtractionClient(cfg)
    return OpenAIVisionExtractionClient(cfg)


def build_transcription_client(settings: Settings) -> TranscriptionClient | None:
    cfg = settings.transcription
    if not cfg.enabled:
        return None
    if cfg.engine == "whisperlive":
        return WhisperLiveTranscriptionClient(cfg)
    raise ValueError(f"unknown transcription engine: {cfg.engine}")


def build_embedding_client(settings: Settings) -> EmbeddingClient | None:
    cfg = settings.embedding
    if not cfg.enabled:
        return None
    return OpenAIEmbeddingClient(cfg)
