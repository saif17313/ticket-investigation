"""Top-level investigation service orchestration."""

from __future__ import annotations

from app.core.analyzer import analyze_ticket
from app.core.config import Settings
from app.schemas.models import AnalyzeTicketRequest, AnalyzeTicketResponse
from app.services.ai_fact_extractor import AIFactExtractor


class InvestigatorService:
    """Coordinate one request through the deterministic-plus-optional-AI pipeline."""

    def __init__(self, settings: Settings, ai_extractor: AIFactExtractor) -> None:
        self._settings = settings
        self._ai_extractor = ai_extractor

    async def analyze(self, request: AnalyzeTicketRequest) -> AnalyzeTicketResponse:
        return await analyze_ticket(
            request,
            ai_extractor=self._ai_extractor,
            settings=self._settings,
        )
