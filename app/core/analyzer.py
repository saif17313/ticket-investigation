"""Single deterministic orchestrator for QueueStorm ticket analysis."""

import logging

from app.core.classifier import classify_case
from app.core.config import Settings, get_settings
from app.core.evidence import decide_evidence
from app.core.facts import extract_rule_facts, merge_facts
from app.core.replies import generate_texts
from app.core.routing import requires_human_review, route_department
from app.core.safety import enforce_safety, scan_input_safety
from app.core.severity import decide_severity
from app.schemas.enums import CaseType
from app.schemas.models import AnalyzeTicketRequest, AnalyzeTicketResponse
from app.services.ai_fact_extractor import AIFactExtractor
from app.utils.text import bangla_is_dominant

logger = logging.getLogger(__name__)


def _deduplicate_reason_codes(codes: list[str]) -> list[str]:
    return list(dict.fromkeys(code for code in codes if code))


async def analyze_ticket(
    request: AnalyzeTicketRequest,
    ai_extractor: AIFactExtractor | None = None,
    settings: Settings | None = None,
) -> AnalyzeTicketResponse:
    """Analyze one validated request through the full investigation pipeline."""
    settings = settings or get_settings()
    safety_scan = scan_input_safety(request.complaint)
    classification = classify_case(request)

    # Safety reports take precedence over financial classification. Prompt
    # injection alone does not force a phishing case; it is handled as a guardrail.
    if safety_scan.force_phishing and classification.case_type != CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        classification = type(classification)(
            CaseType.PHISHING_OR_SOCIAL_ENGINEERING,
            ["phishing_or_social_engineering"],
        )

    rule_result = extract_rule_facts(
        request,
        classification.case_type,
        safety_flags=safety_scan.reason_codes,
    )
    ai_result = None
    if (
        ai_extractor is not None
        and settings.llm_enabled
        and rule_result.confidence < settings.rule_confidence_threshold
    ):
        try:
            ai_result = await ai_extractor.extract_facts(request, rule_result)
        except Exception as exc:  # noqa: BLE001 - optional AI must fail safely
            logger.warning(
                "ai_extractor_failed",
                extra={"ticket_id": request.ticket_id, "exc_type": type(exc).__name__},
            )
            ai_result = None

    merged_facts = merge_facts(rule_result, ai_result)
    evidence = decide_evidence(request, classification.case_type, merged_facts.facts)
    department = route_department(request, classification.case_type)
    matched_amount = evidence.relevant_transaction.amount if evidence.relevant_transaction else None
    severity = decide_severity(request, classification.case_type, matched_amount)
    human_review_required = requires_human_review(
        classification.case_type,
        evidence.evidence_verdict,
        severity,
        evidence.relevant_transaction_id,
    )
    texts = generate_texts(request, classification.case_type, evidence, department, severity)
    response = AnalyzeTicketResponse(
        ticket_id=request.ticket_id,
        relevant_transaction_id=evidence.relevant_transaction_id,
        evidence_verdict=evidence.evidence_verdict,
        case_type=classification.case_type,
        severity=severity,
        department=department,
        agent_summary=texts.agent_summary,
        recommended_next_action=texts.recommended_next_action,
        customer_reply=texts.customer_reply,
        human_review_required=human_review_required,
        confidence=evidence.confidence,
        reason_codes=_deduplicate_reason_codes(classification.reason_codes + evidence.reason_codes),
    )
    bangla = (request.language is not None and request.language.value == "bn") or bangla_is_dominant(request.complaint)
    return enforce_safety(response, bangla=bangla)
