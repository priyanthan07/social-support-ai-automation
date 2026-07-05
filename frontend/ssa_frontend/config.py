"""Frontend configuration (reads layered env files like the backend)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_files() -> tuple[str, ...]:
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


class FrontendSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "dev"
    backend_api_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> FrontendSettings:
    return FrontendSettings()
