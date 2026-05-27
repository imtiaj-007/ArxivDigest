"""Typed application settings. Reads from environment + .env file."""

from __future__ import annotations

from dotenv import find_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from env vars and .env (if present).

    All observability credentials are optional — when absent, the related
    SDK no-ops silently, so the agent runs the same with or without them.
    """

    # Runtime
    app_env: str = Field(default="development", description="development | staging | production")
    log_level: str = Field(default="INFO", description="Python logging level name")

    # Database — required at runtime, not at import (so tests / --help work without it)
    database_url: str | None = None

    # LLM providers
    groq_api_key: str | None = None
    gemini_api_key: str | None = None

    # Embeddings
    voyage_api_key: str | None = None

    # Langfuse
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # Sentry
    sentry_dsn: str | None = None
    sentry_environment: str = "development"

    # find_dotenv walks up from CWD to locate a .env — lets a single repo-root .env
    # serve every workspace without per-package duplication.
    model_config = SettingsConfigDict(
        env_file=find_dotenv(usecwd=True) or ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Cached settings singleton. Lazily constructed so importing config.py is cheap."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
