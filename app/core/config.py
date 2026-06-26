"""Typed runtime configuration for QueueStorm Investigator."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError:
        return default


class Settings(BaseModel):
    """Process settings loaded from environment variables.

    AI is intentionally disabled by default. The deterministic rule engine is
    the source of truth and must remain fully functional without secrets,
    network access, or optional AI packages.
    """

    llm_enabled: bool = Field(default=False)
    gemini_api_key: str | None = Field(default=None)
    gemini_model: str = Field(default="gemini-2.5-flash")
    llm_timeout_seconds: float = Field(default=4.0, ge=0.1, le=30.0)
    rule_confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached runtime settings."""

    return Settings(
        llm_enabled=_env_bool("LLM_ENABLED", False),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        gemini_model=os.getenv("GEMINI_MODEL") or "gemini-2.5-flash",
        llm_timeout_seconds=_env_float("LLM_TIMEOUT_SECONDS", 4.0),
        rule_confidence_threshold=_env_float("RULE_CONFIDENCE_THRESHOLD", 0.75),
        log_level=(os.getenv("LOG_LEVEL") or "INFO").upper(),  # type: ignore[arg-type]
    )
