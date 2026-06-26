"""Shared pytest fixtures."""

from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _disable_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default every test to safe-mode (no live LLM calls)."""

    monkeypatch.setenv("LLM_ENABLED", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "")


@pytest.fixture
def client() -> Any:
    """FastAPI test client (synchronous)."""

    # Reset lru_caches so monkeypatched env vars take effect per test.
    from app.api import deps
    from app.core.config import get_settings

    get_settings.cache_clear()
    deps._rule_engine_singleton.cache_clear()
    deps._ai_service_singleton.cache_clear()
    deps._investigator_singleton.cache_clear()

    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def sample_payload() -> dict[str, Any]:
    """The canonical sample request body used by integration tests."""

    return {
        "ticket_id": "T-1001",
        "complaint": "I sent 5000 to the wrong number yesterday",
        "language": "en",
        "channel": "app",
        "user_type": "retail",
        "campaign_context": "",
        "transaction_history": [
            {
                "transaction_id": "TX1001",
                "timestamp": "2025-01-01T00:00:00Z",
                "type": "transfer",
                "amount": 5000.0,
                "counterparty": "+8801712345678",
                "status": "completed",
            }
        ],
        "metadata": {"device": "android"},
    }