"""Text embeddings via an OpenAI-compatible endpoint (e.g. vLLM serving
bge-m3). Model + dimension come from config."""

from __future__ import annotations

from openai import AsyncOpenAI

from app.config import EmbeddingConfig
from app.inference.base import EmbeddingClient, InferenceUnavailable


class OpenAIEmbeddingClient(EmbeddingClient):
    def __init__(self, cfg: EmbeddingConfig) -> None:
        self._cfg = cfg
        self._client = AsyncOpenAI(base_url=cfg.base_url, api_key="not-needed-local")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            resp = await self._client.embeddings.create(
                model=self._cfg.model, input=texts
            )
        except Exception as exc:  # noqa: BLE001
            raise InferenceUnavailable(f"embedding backend error: {exc}") from exc
        return [d.embedding for d in resp.data]

    @property
    def dim(self) -> int:
        return self._cfg.dim

    async def healthy(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:  # noqa: BLE001
            return False
