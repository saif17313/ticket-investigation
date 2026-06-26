"""Centralized application configuration.

All runtime configuration is loaded from environment variables (or a `.env`
file during local development) into a single typed ``Settings`` object. The
object is exposed via :func:`get_settings` which is cached so the application
sees exactly one instance per process. This is the only place where environment
variables should be read.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application configuration.

    Values are read in this order of precedence:
    1. Real process environment variables (highest priority — used in Docker).
    2. Variables defined in a local ``.env`` file.
    3. Field defaults declared below (lowest priority).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Gemini / AI integration -------------------------------------------------
    # The API key is intentionally optional so the service can boot in
    # environments without credentials (e.g. local development, CI tests).
    # When LLM_ENABLED is true and a narrative is required, the AI service is
    # responsible for surfacing a clear configuration error.
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    # --- Runtime toggles --------------------------------------------------------
    llm_enabled: bool = Field(default=True, alias="LLM_ENABLED")
    llm_timeout_seconds: float = Field(default=8.0, alias="LLM_TIMEOUT_SECONDS")

    # --- Business thresholds ----------------------------------------------------
    # Transactions at or above this absolute amount are treated as high value
    # by the rule engine and influence severity / human review decisions.
    high_value_threshold: float = Field(default=10_000.0, alias="HIGH_VALUE_THRESHOLD")

    # --- Observability ----------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide :class:`Settings` instance.

    ``lru_cache`` guarantees a single object per process, which keeps
    configuration immutable after startup and makes the object trivially
    injectable into FastAPI dependencies and services.
    """

    return Settings()