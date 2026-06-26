"""AI service interface.

The AI module is **only** responsible for the three narrative fields:

- ``agent_summary``
- ``recommended_next_action``
- ``customer_reply``

It must **not** decide the transaction match, evidence verdict, severity,
or department. This Protocol enforces that boundary structurally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.models import InvestigationDecision
from app.schemas import AnalyzeRequest


@dataclass(frozen=True)
class Narrative:
    """The three strings the AI module is allowed to produce."""

    agent_summary: str
    recommended_next_action: str
    customer_reply: str


@runtime_checkable
class AIService(Protocol):
    """Contract every AI implementation must satisfy."""

    async def narrate(
        self,
        request: AnalyzeRequest,
        decision: InvestigationDecision,
    ) -> Narrative:
        """Return the three narrative fields for the given ticket."""
        ...