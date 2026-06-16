"""Application configuration.

Everything is loaded from environment variables (see .env.example). The
inference settings here are the *only* place model identities are named —
satisfying NFR-7: swapping a model is a config change, never a code change.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExtractionConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INFERENCE_EXTRACTION_")
    enabled: bool = True
    base_url: str = "http://vllm:8000/v1"
    model: str = "Qwen/Qwen2.5-VL-7B-Instruct"
    api_key: str = "not-needed-local"


class TranscriptionConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INFERENCE_TRANSCRIPTION_")
    enabled: bool = True
    engine: str = "whisperlive"
    model: str = "large-v3-turbo"
    ws_url: str = "ws://whisperlive:9090"
    vad: bool = True


class EmbeddingConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INFERENCE_EMBEDDING_")
    enabled: bool = True
    base_url: str = "http://vllm-embed:8000/v1"
    model: str = "BAAI/bge-m3"
    dim: int = 1024


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_timezone: str = "Asia/Kolkata"
    date_display_format: str = "DD MMM YYYY"  # NFR-5

    postgres_user: str = "notes"
    postgres_password: str = "change-me-in-prod"
    postgres_db: str = "notes"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    storage_root: str = "/data/storage"

    # Optional full override (e.g. sqlite for local dev). When unset, the URL
    # is assembled from the postgres_* parts below (prod / compose).
    database_url_override: str | None = None

    keycloak_url: str = "http://keycloak:8080"
    keycloak_realm: str = "notes"
    keycloak_client_id: str = "notes-frontend"

    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
