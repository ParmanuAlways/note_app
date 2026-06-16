"""FastAPI application entrypoint.

Inference clients are built once at startup and stashed on app.state. If a
backend is disabled/unreachable the app still starts (NFR-9) — the status page
reports the degraded state instead of crashing.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging

from app.api import documents, events, extractions, notes, status, tasks, trash
from app.config import get_settings
from app.db.database import init_db
from app.inference.factory import (
    build_embedding_client,
    build_extraction_client,
    build_transcription_client,
)

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.extraction_client = build_extraction_client(settings)
    app.state.transcription_client = build_transcription_client(settings)
    app.state.embedding_client = build_embedding_client(settings)
    # The DB is core infra (unlike inference, NFR-9). If it's down we log and
    # still boot, so /health and the status page stay available for diagnosis.
    try:
        init_db()
    except Exception as exc:  # noqa: BLE001
        logger.warning("init_db failed (DB unreachable?): %s", exc)
    yield


app = FastAPI(title="AI Notes & Scheduler", version="0.1.0", lifespan=lifespan)

# Local-only origins (browser client on the same air-gapped host). No external
# origins — consistent with NFR-3.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status.router)
app.include_router(events.router)
app.include_router(tasks.router)
app.include_router(documents.router)
app.include_router(notes.router)
app.include_router(trash.router)
app.include_router(extractions.router)
