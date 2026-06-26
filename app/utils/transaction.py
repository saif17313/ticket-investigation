"""Transaction normalization, matching, and duplicate-detection helpers."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from itertools import combinations

from app.schemas.enums import CaseType, TransactionStatus, TransactionType
from app.schemas.models import TransactionHistoryItem
from app.utils.text import extract_amounts, extract_approximate_hour, extract_phone_numbers, extract_transaction_ids


def normalize_counterparty(value: str | None) -> str:
    """Normalize phones while retaining meaningful merchant and agent identifiers."""
    if not value:
        return ""
    raw = value.strip()
    digits = "".join(char for char in raw if char.isdigit())
    if len(digits) >= 10:
        if digits.startswith("01") and len(digits) == 11:
            return f"880{digits[1:]}"
        if digits.startswith("8801"):
            return digits
    return "".join(char for char in raw.upper() if char.isalnum())


def _timestamp_number(value: datetime | None) -> float:
    if value is None:
        return float("-inf")
    try:
        return value.timestamp()
    except (OverflowError, OSError, ValueError):
        return float("-inf")


def sort_transactions(transactions: list[TransactionHistoryItem]) -> list[TransactionHistoryItem]:
    return sorted(transactions, key=lambda transaction: _timestamp_number(transaction.timestamp), reverse=True)


def same_recipient_history(
    transactions: list[TransactionHistoryItem], counterparty: str | None
) -> list[TransactionHistoryItem]:
    normalized = normalize_counterparty(counterparty)
    if not normalized:
        return []
    return [
        transaction
        for transaction in transactions
        if normalize_counterparty(transaction.counterparty) == normalized
    ]


def group_duplicate_transactions(
    transactions: list[TransactionHistoryItem], window_seconds: int = 300
) -> list[list[TransactionHistoryItem]]:
    """Return groups of same-payee, same-type, same-value transactions close in time."""
    buckets: dict[tuple[str, str, float], list[TransactionHistoryItem]] = defaultdict(list)
    for transaction in transactions:
        if (
            transaction.type is None
            or transaction.amount is None
            or not normalize_counterparty(transaction.counterparty)
            or transaction.timestamp is None
            or transaction.status not in {TransactionStatus.COMPLETED, TransactionStatus.PENDING}
        ):
            continue
        key = (
            transaction.type.value,
            normalize_counterparty(transaction.counterparty),
            round(transaction.amount, 2),
        )
        buckets[key].append(transaction)

    groups: list[list[TransactionHistoryItem]] = []
    for bucket in buckets.values():
        ordered = sorted(bucket, key=lambda item: _timestamp_number(item.timestamp))
        current_group: list[TransactionHistoryItem] = []
        for transaction in ordered:
            if not current_group:
                current_group = [transaction]
                continue
            gap = _timestamp_number(transaction.timestamp) - _timestamp_number(current_group[-1].timestamp)
            if gap <= window_seconds:
                current_group.append(transaction)
            else:
                if len(current_group) >= 2:
                    groups.append(current_group)
                current_group = [transaction]
        if len(current_group) >= 2:
            groups.append(current_group)
    return groups


def find_suspected_duplicate(
    transactions: list[TransactionHistoryItem], window_seconds: int = 300
) -> TransactionHistoryItem | None:
    """Return the later member of the strongest duplicate group."""
    duplicate_groups = group_duplicate_transactions(transactions, window_seconds)
    if not duplicate_groups:
        return None
    candidate_group = max(
        duplicate_groups,
        key=lambda group: _timestamp_number(group[-1].timestamp),
    )
    return candidate_group[-1]


def score_transaction_match(
    transaction: TransactionHistoryItem,
    complaint: str,
    case_type: CaseType,
) -> int:
    """Score only observable complaint/evidence alignment; higher is better."""
    score = 0
    explicit_ids = extract_transaction_ids(complaint)
    if explicit_ids and transaction.transaction_id and transaction.transaction_id.upper() in explicit_ids:
        score += 100

    amounts = extract_amounts(complaint)
    if transaction.amount is not None and any(abs(transaction.amount - amount) < 0.01 for amount in amounts):
        score += 40

    expected_types: dict[CaseType, set[TransactionType]] = {
        CaseType.WRONG_TRANSFER: {TransactionType.TRANSFER},
        CaseType.PAYMENT_FAILED: {TransactionType.PAYMENT, TransactionType.TRANSFER},
        CaseType.REFUND_REQUEST: {TransactionType.PAYMENT, TransactionType.REFUND},
        CaseType.MERCHANT_SETTLEMENT_DELAY: {TransactionType.SETTLEMENT},
        CaseType.AGENT_CASH_IN_ISSUE: {TransactionType.CASH_IN},
    }
    if case_type in expected_types and transaction.type is not None:
        score += 20 if transaction.type in expected_types[case_type] else -10

    complaint_phones = extract_phone_numbers(complaint)
    if complaint_phones and normalize_counterparty(transaction.counterparty) in complaint_phones:
        score += 20

    complaint_hour = extract_approximate_hour(complaint)
    if complaint_hour is not None and transaction.timestamp is not None:
        distance = abs(transaction.timestamp.hour - complaint_hour)
        if min(distance, 24 - distance) <= 1:
            score += 10

    # Recent transactions are a light tiebreaker, never enough to invent a match.
    if transaction.timestamp is not None:
        score += 1
    return score
