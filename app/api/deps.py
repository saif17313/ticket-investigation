"""FastAPI dependency providers.

Each provider returns a single, process-wide object so route handlers stay
declarative: they declare *what* they need, not *how* to build it. This is
also where tests inject stubs/mocks by overriding these dependencies.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.services.ai_service import AIService
from app.services.gemini_service import GeminiService
from app.services.investigator import InvestigatorService
from app.services.rule_engine import RuleEngine, StubRuleEngine


@lru_cache(maxsize=1)
def _rule_engine_singleton() -> RuleEngine:
    """Real rule engine is plugged in here. Until then we ship the stub."""

    return StubRuleEngine()


@lru_cache(maxsize=1)
def _ai_service_singleton() -> AIService:
    """Construct the AI service once per process, bound to current settings."""

    return GeminiService(get_settings())


@lru_cache(maxsize=1)
def _investigator_singleton() -> InvestigatorService:
    """Construct the orchestrator once per process."""

    return InvestigatorService(
        rule_engine=_rule_engine_singleton(),
        ai_service=_ai_service_singleton(),
    )


def provide_investigator() -> InvestigatorService:
    """FastAPI dependency: returns the singleton orchestrator."""

    return _investigator_singleton()


def provide_rule_engine() -> RuleEngine:
    """FastAPI dependency: returns the singleton rule engine."""

    return _rule_engine_singleton()