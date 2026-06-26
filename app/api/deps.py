"""FastAPI dependency providers."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.services.ai_fact_extractor import AIFactExtractor, GeminiFactExtractor
from app.services.investigator import InvestigatorService


@lru_cache(maxsize=1)
def _settings_singleton() -> Settings:
    return get_settings()


@lru_cache(maxsize=1)
def _ai_extractor_singleton() -> AIFactExtractor:
    return GeminiFactExtractor(_settings_singleton())


@lru_cache(maxsize=1)
def _investigator_singleton() -> InvestigatorService:
    return InvestigatorService(
        settings=_settings_singleton(),
        ai_extractor=_ai_extractor_singleton(),
    )


def provide_settings() -> Settings:
    return _settings_singleton()


def provide_ai_extractor() -> AIFactExtractor:
    return _ai_extractor_singleton()


def provide_investigator() -> InvestigatorService:
    return _investigator_singleton()
