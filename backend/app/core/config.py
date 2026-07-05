"""Typed application configuration.

Loads settings using the layered env-file scheme:

1. A common ``.env`` sets ``APP_ENV`` (dev | prod) and shared defaults.
2. ``.env.<APP_ENV>`` overrides values from ``.env``.
3. Real OS environment variables override everything (used in containers,
   where docker-compose injects the env files as process environment vars).

A single cached ``Settings`` instance is exposed via ``get_settings()`` and
must be the only source of configuration in the codebase (no scattered
``os.getenv`` calls).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_files() -> tuple[str, ...]:
    """Return the ordered env files to load: (.env, .env.<APP_ENV>).

    Later files take priority (pydantic-settings semantics).
    """
    app_env = os.getenv("APP_ENV")
    common = Path(".env")
    if not app_env and common.exists():
        for raw in common.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("APP_ENV="):
                app_env = line.split("=", 1)[1].strip()
                break
    app_env = (app_env or "dev").strip()
    return (".env", f".env.{app_env}")


class Settings(BaseSettings):
    """Application settings, populated from the environment."""

    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General ---
    app_env: str = "dev"
    log_level: str = "INFO"
    app_name: str = "Social Support AI Automation"

    # --- PostgreSQL ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "social"
    postgres_password: str = "social_dev_pw"
    postgres_db: str = "social_support"

    # --- MongoDB ---
    mongo_uri: str = "mongodb://mongo_root:mongo_dev_pw@localhost:27017"
    mongo_db: str = "social_support"

    # --- Qdrant ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "enablement_kb"

    # --- Neo4j ---
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_dev_pw"

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "qwen2.5:3b-instruct"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_request_timeout: int = 180
    enable_vision: bool = False
    ollama_vision_model: str = "llava:7b"

    # --- LLM concurrency guard (serialize calls to a CPU-only Ollama) ---
    llm_max_concurrency: int = 1

    # --- Langfuse observability ---
    langfuse_enabled: bool = True
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # --- ML artifacts + uploads ---
    ml_artifacts_dir: str = "/artifacts"
    upload_dir: str = "/app/uploads"

    # --- Frontend -> backend base URL ---
    backend_api_url: str = "http://localhost:8000"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """SQLAlchemy URL using the psycopg (v3) driver."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "prod"

    @property
    def langfuse_ready(self) -> bool:
        """True only when Langfuse is enabled and credentials are present."""
        return bool(
            self.langfuse_enabled
            and self.langfuse_public_key
            and self.langfuse_secret_key
            and not self.langfuse_public_key.endswith("xxxxxxxx")
        )


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings singleton."""
    return Settings()


settings = get_settings()
