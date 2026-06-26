"""Severity selection based on case type, amount, and risk indicators."""

from app.schemas.enums import CaseType, Severity
from app.schemas.models import AnalyzeTicketRequest
from app.utils.text import extract_amounts, has_any


def decide_severity(request: AnalyzeTicketRequest, case_type: CaseType, matched_amount: float | None) -> Severity:
    amounts = extract_amounts(request.complaint)
    if matched_amount is not None:
        amounts.append(matched_amount)
    largest_amount = max(amounts, default=0.0)

    if largest_amount >= 50000:
        return Severity.CRITICAL
    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return Severity.CRITICAL
    if case_type in {CaseType.DUPLICATE_PAYMENT, CaseType.AGENT_CASH_IN_ISSUE}:
        return Severity.HIGH
    if case_type == CaseType.PAYMENT_FAILED:
        if has_any(request.complaint, ("deducted", "money cut", "balance", "কেটে")):
            return Severity.HIGH
        return Severity.MEDIUM
    if case_type == CaseType.WRONG_TRANSFER:
        return Severity.HIGH if largest_amount >= 5000 else Severity.MEDIUM
    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        return Severity.MEDIUM
    if case_type == CaseType.REFUND_REQUEST:
        if has_any(request.complaint, ("changed my mind", "do not want", "পণ্য চাই না")) and largest_amount <= 1000:
            return Severity.LOW
        return Severity.HIGH if largest_amount >= 5000 else Severity.MEDIUM
    return Severity.LOW
