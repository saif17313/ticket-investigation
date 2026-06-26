"""Evidence-first transaction matching and case-specific verdict rules."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.enums import CaseType, EvidenceVerdict, TransactionStatus, TransactionType
from app.schemas.models import AnalyzeTicketRequest, TransactionHistoryItem
from app.utils.text import has_any
from app.utils.transaction import (
    find_suspected_duplicate,
    same_recipient_history,
    score_transaction_match,
    sort_transactions,
)


@dataclass(frozen=True)
class EvidenceDecision:
    relevant_transaction: TransactionHistoryItem | None
    evidence_verdict: EvidenceVerdict
    confidence: float
    reason_codes: list[str]

    @property
    def relevant_transaction_id(self) -> str | None:
        return self.relevant_transaction.transaction_id if self.relevant_transaction else None


@dataclass(frozen=True)
class CandidateSelection:
    transaction: TransactionHistoryItem | None
    ambiguous: bool = False


def _select_candidate(request: AnalyzeTicketRequest, case_type: CaseType) -> CandidateSelection:
    scored = [
        (score_transaction_match(transaction, request.complaint, case_type), transaction)
        for transaction in request.transaction_history
    ]
    scored = [(score, transaction) for score, transaction in scored if score >= 20]
    if not scored:
        return CandidateSelection(None)

    scored.sort(key=lambda item: (item[0], item[1].timestamp is not None), reverse=True)
    top_score, top_transaction = scored[0]
    equally_plausible = [transaction for score, transaction in scored if score == top_score]
    if len(equally_plausible) > 1:
        return CandidateSelection(None, ambiguous=True)
    return CandidateSelection(top_transaction)


def _no_match(reason: str = "no_matching_transaction") -> EvidenceDecision:
    return EvidenceDecision(None, EvidenceVerdict.INSUFFICIENT_DATA, 0.55, [reason])


def _candidate_or_insufficient(selection: CandidateSelection) -> EvidenceDecision | None:
    if selection.ambiguous:
        return EvidenceDecision(
            None,
            EvidenceVerdict.INSUFFICIENT_DATA,
            0.65,
            ["ambiguous_transaction_match"],
        )
    if selection.transaction is None:
        return _no_match()
    return None


def _wrong_transfer(request: AnalyzeTicketRequest) -> EvidenceDecision:
    selection = _select_candidate(request, CaseType.WRONG_TRANSFER)
    insufficient = _candidate_or_insufficient(selection)
    if insufficient:
        return insufficient
    transaction = selection.transaction
    assert transaction is not None
    if transaction.type != TransactionType.TRANSFER or transaction.status != TransactionStatus.COMPLETED:
        return EvidenceDecision(
            transaction,
            EvidenceVerdict.INCONSISTENT,
            0.72,
            ["wrong_transfer_claim", "transaction_type_or_status_conflict"],
        )
    established_transfers = [
        item
        for item in same_recipient_history(request.transaction_history, transaction.counterparty)
        if item.type == TransactionType.TRANSFER and item.status == TransactionStatus.COMPLETED
    ]
    if len(established_transfers) >= 3:
        return EvidenceDecision(
            transaction,
            EvidenceVerdict.INCONSISTENT,
            0.75,
            ["wrong_transfer_claim", "established_recipient_pattern", "evidence_inconsistent"],
        )
    return EvidenceDecision(
        transaction,
        EvidenceVerdict.CONSISTENT,
        0.90,
        ["wrong_transfer", "transaction_match"],
    )


def _payment_failed(request: AnalyzeTicketRequest) -> EvidenceDecision:
    selection = _select_candidate(request, CaseType.PAYMENT_FAILED)
    insufficient = _candidate_or_insufficient(selection)
    if insufficient:
        return insufficient
    transaction = selection.transaction
    assert transaction is not None
    if transaction.type not in {TransactionType.PAYMENT, TransactionType.TRANSFER}:
        return EvidenceDecision(transaction, EvidenceVerdict.INCONSISTENT, 0.70, ["transaction_type_conflict"])
    if transaction.status in {TransactionStatus.FAILED, TransactionStatus.PENDING, TransactionStatus.REVERSED}:
        return EvidenceDecision(
            transaction,
            EvidenceVerdict.CONSISTENT,
            0.90,
            ["payment_failed", "potential_balance_deduction"],
        )
    if transaction.status == TransactionStatus.COMPLETED:
        return EvidenceDecision(
            transaction,
            EvidenceVerdict.INCONSISTENT,
            0.80,
            ["payment_failed_claim", "completed_transaction"],
        )
    return EvidenceDecision(transaction, EvidenceVerdict.INSUFFICIENT_DATA, 0.60, ["transaction_status_missing"])


def _refund_request(request: AnalyzeTicketRequest) -> EvidenceDecision:
    selection = _select_candidate(request, CaseType.REFUND_REQUEST)
    insufficient = _candidate_or_insufficient(selection)
    if insufficient:
        return insufficient
    transaction = selection.transaction
    assert transaction is not None
    not_received = has_any(request.complaint, ("not received", "did not receive", "haven't received", "পাইনি", "পাই নি"))
    if transaction.type == TransactionType.REFUND and transaction.status == TransactionStatus.COMPLETED and not_received:
        return EvidenceDecision(transaction, EvidenceVerdict.INCONSISTENT, 0.82, ["refund_completed_record"])
    if transaction.type == TransactionType.PAYMENT and transaction.status == TransactionStatus.COMPLETED:
        return EvidenceDecision(transaction, EvidenceVerdict.CONSISTENT, 0.85, ["refund_request", "completed_merchant_payment"])
    if transaction.type not in {TransactionType.PAYMENT, TransactionType.REFUND}:
        return EvidenceDecision(transaction, EvidenceVerdict.INCONSISTENT, 0.70, ["transaction_type_conflict"])
    return EvidenceDecision(transaction, EvidenceVerdict.INSUFFICIENT_DATA, 0.60, ["refund_evidence_incomplete"])


def _duplicate_payment(request: AnalyzeTicketRequest) -> EvidenceDecision:
    duplicate = find_suspected_duplicate(request.transaction_history)
    if duplicate is not None:
        return EvidenceDecision(
            duplicate,
            EvidenceVerdict.CONSISTENT,
            0.93,
            ["duplicate_payment", "duplicate_transaction_pattern"],
        )
    selection = _select_candidate(request, CaseType.DUPLICATE_PAYMENT)
    if selection.ambiguous:
        return EvidenceDecision(None, EvidenceVerdict.INSUFFICIENT_DATA, 0.65, ["ambiguous_transaction_match"])
    if selection.transaction is not None:
        return EvidenceDecision(
            selection.transaction,
            EvidenceVerdict.INCONSISTENT,
            0.76,
            ["duplicate_payment_claim", "single_matching_transaction"],
        )
    return _no_match()


def _merchant_settlement(request: AnalyzeTicketRequest) -> EvidenceDecision:
    selection = _select_candidate(request, CaseType.MERCHANT_SETTLEMENT_DELAY)
    insufficient = _candidate_or_insufficient(selection)
    if insufficient:
        return insufficient
    transaction = selection.transaction
    assert transaction is not None
    if transaction.type != TransactionType.SETTLEMENT:
        return EvidenceDecision(transaction, EvidenceVerdict.INCONSISTENT, 0.70, ["transaction_type_conflict"])
    if transaction.status == TransactionStatus.PENDING:
        return EvidenceDecision(transaction, EvidenceVerdict.CONSISTENT, 0.92, ["pending_settlement"])
    if transaction.status == TransactionStatus.COMPLETED:
        return EvidenceDecision(transaction, EvidenceVerdict.INCONSISTENT, 0.82, ["completed_settlement"])
    return EvidenceDecision(transaction, EvidenceVerdict.INSUFFICIENT_DATA, 0.60, ["settlement_status_inconclusive"])


def _agent_cash_in(request: AnalyzeTicketRequest) -> EvidenceDecision:
    selection = _select_candidate(request, CaseType.AGENT_CASH_IN_ISSUE)
    insufficient = _candidate_or_insufficient(selection)
    if insufficient:
        return insufficient
    transaction = selection.transaction
    assert transaction is not None
    if transaction.type != TransactionType.CASH_IN:
        return EvidenceDecision(transaction, EvidenceVerdict.INCONSISTENT, 0.70, ["transaction_type_conflict"])
    if transaction.status in {TransactionStatus.PENDING, TransactionStatus.FAILED}:
        return EvidenceDecision(transaction, EvidenceVerdict.CONSISTENT, 0.88, ["cash_in_pending_or_failed"])
    if transaction.status == TransactionStatus.COMPLETED:
        return EvidenceDecision(transaction, EvidenceVerdict.INCONSISTENT, 0.80, ["completed_cash_in_record"])
    return EvidenceDecision(transaction, EvidenceVerdict.INSUFFICIENT_DATA, 0.60, ["cash_in_status_inconclusive"])


def decide_evidence(request: AnalyzeTicketRequest, case_type: CaseType) -> EvidenceDecision:
    """Apply the published evidence policy for a classified case."""
    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return EvidenceDecision(None, EvidenceVerdict.INSUFFICIENT_DATA, 0.95, ["phishing_report"])
    if case_type == CaseType.WRONG_TRANSFER:
        return _wrong_transfer(request)
    if case_type == CaseType.PAYMENT_FAILED:
        return _payment_failed(request)
    if case_type == CaseType.REFUND_REQUEST:
        return _refund_request(request)
    if case_type == CaseType.DUPLICATE_PAYMENT:
        return _duplicate_payment(request)
    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        return _merchant_settlement(request)
    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        return _agent_cash_in(request)
    return EvidenceDecision(None, EvidenceVerdict.INSUFFICIENT_DATA, 0.60, ["insufficient_data"])
