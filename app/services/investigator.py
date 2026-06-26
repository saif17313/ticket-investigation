"""Top-level orchestrator: rule engine → AI → safety filter → response.

This service is the only place where the deterministic decision and the AI
narrative are joined. Keeping the join here (instead of in a route handler)
means the orchestration is independently testable.
"""

from __future__ import annotations

from app.models import InvestigationDecision
from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.ai_service import AIService, Narrative
from app.services.rule_engine import RuleEngine
from app.utils.safety import sanitize


class InvestigatorService:
    """Coordinates one ticket through the full investigation pipeline."""

    def __init__(self, rule_engine: RuleEngine, ai_service: AIService) -> None:
        self._rule_engine = rule_engine
        self._ai_service = ai_service

    async def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        decision: InvestigationDecision = self._rule_engine.decide(request)
        narrative: Narrative = await self._ai_service.narrate(request, decision)

        safe_narrative, repaired = sanitize(narrative)
        human_review = decision.human_review_required or repaired

        return AnalyzeResponse(
            ticket_id=request.ticket_id,
            relevant_transaction_id=decision.relevant_transaction_id,
            evidence_verdict=decision.evidence_verdict,
            case_type=decision.case_type,
            severity=decision.severity,
            department=decision.department,
            agent_summary=safe_narrative.agent_summary,
            recommended_next_action=safe_narrative.recommended_next_action,
            customer_reply=safe_narrative.customer_reply,
            human_review_required=human_review,
            confidence=decision.confidence,
            reason_codes=decision.reason_codes,
        )
