"""Department routing and human-review decisions."""

from app.schemas.enums import CaseType, Department, EvidenceVerdict, Severity
from app.schemas.models import AnalyzeTicketRequest
from app.utils.text import has_any


def route_department(request: AnalyzeTicketRequest, case_type: CaseType) -> Department:
    if case_type == CaseType.WRONG_TRANSFER:
        return Department.DISPUTE_RESOLUTION
    if case_type in {CaseType.PAYMENT_FAILED, CaseType.DUPLICATE_PAYMENT}:
        return Department.PAYMENTS_OPS
    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        return Department.MERCHANT_OPERATIONS
    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        return Department.AGENT_OPERATIONS
    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return Department.FRAUD_RISK
    if case_type == CaseType.REFUND_REQUEST and has_any(
        request.complaint, ("dispute", "not received", "fraud", "ভুল", "পাইনি")
    ):
        return Department.DISPUTE_RESOLUTION
    return Department.CUSTOMER_SUPPORT


def requires_human_review(
    case_type: CaseType,
    verdict: EvidenceVerdict,
    severity: Severity,
    relevant_transaction_id: str | None,
) -> bool:
    """Escalate risky and contradictory cases while preserving sample exceptions."""
    if case_type in {
        CaseType.PHISHING_OR_SOCIAL_ENGINEERING,
        CaseType.DUPLICATE_PAYMENT,
        CaseType.AGENT_CASH_IN_ISSUE,
    }:
        return True
    if case_type == CaseType.WRONG_TRANSFER:
        return relevant_transaction_id is not None or verdict == EvidenceVerdict.INCONSISTENT
    if verdict == EvidenceVerdict.INCONSISTENT:
        return True
    # A clear failed payment follows a standard operations path without manual review.
    if case_type == CaseType.PAYMENT_FAILED and verdict == EvidenceVerdict.CONSISTENT:
        return False
    if case_type == CaseType.REFUND_REQUEST and severity == Severity.LOW:
        return False
    return severity in {Severity.HIGH, Severity.CRITICAL}
