"""System status (FR-41) + health. On a self-managed air-gapped server with no
vendor monitoring, this is the first-line diagnostic when extraction stops."""

from __future__ import annotations

import shutil

from fastapi import APIRouter, Request

router = APIRouter(tags=["status"])


@router.get("/health")
async def health() -> dict:
    """Liveness only — must never depend on the GPU (NFR-9)."""
    return {"status": "ok"}


@router.get("/status")
async def status(request: Request) -> dict:
    """Operator dashboard data: inference state, disk, (queue/GPU/backup land
    in later phases). Each inference role degrades independently."""
    state = request.app.state

    async def _probe(client) -> str:
        if client is None:
            return "disabled"
        try:
            return "ready" if await client.healthy() else "unreachable"
        except Exception:  # noqa: BLE001
            return "unreachable"

    disk = shutil.disk_usage("/")
    return {
        "inference": {
            "extraction": await _probe(state.extraction_client),
            "transcription": await _probe(state.transcription_client),
            "embedding": await _probe(state.embedding_client),
        },
        "disk": {
            "total_gb": round(disk.total / 1e9, 1),
            "used_gb": round(disk.used / 1e9, 1),
            "free_gb": round(disk.free / 1e9, 1),
        },
        # Filled in later phases:
        "queue_depth": None,        # Phase 1/2 (batch queue)
        "gpu": None,                # Phase 5
        "last_backup_at": None,     # Phase 5 (FR-39)
    }
