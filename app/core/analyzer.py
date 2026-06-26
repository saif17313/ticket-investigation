"""Single deterministic orchestrator for QueueStorm ticket analysis."""

from app.core.classifier import classify_case
from app.core.evidence import decide_evidence
from app.core.replies import generate_texts
from app.core.routing import requires_human_review, route_department
from app.core.safety import enforce_safety
from app.core.severity import decide_severity
from app.schemas.models import AnalyzeTicketRequest, AnalyzeTicketResponse
from app.utils.text import bangla_is_dominant


def _deduplicate_reason_codes(codes: list[str]) -> list[str]:
    return list(dict.fromkeys(code for code in codes if code))


def analyze_ticket(request: AnalyzeTicketRequest) -> AnalyzeTicketResponse:
    """Analyze one validated request without network calls or mutable state."""
    classification = classify_case(request)
    evidence = decide_evidence(request, classification.case_type)
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
