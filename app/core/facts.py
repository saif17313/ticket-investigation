"""Rule and optional-AI fact extraction models."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from app.schemas.enums import CaseType
from app.schemas.models import AnalyzeTicketRequest
from app.utils.text import (
    extract_amounts,
    extract_approximate_hour,
    extract_phone_numbers,
    extract_transaction_ids,
)


@dataclass(frozen=True)
class ExtractedFacts:
    """Structured facts allowed to influence transaction matching only."""

    transaction_ids: tuple[str, ...] = ()
    amounts: tuple[float, ...] = ()
    phones: tuple[str, ...] = ()
    approximate_hour: int | None = None
    safety_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class FactExtractionResult:
    """A fact bundle and confidence for one extraction source."""

    facts: ExtractedFacts
    confidence: float
    reason_codes: tuple[str, ...] = ()
    source: str = "rules"


EMPTY_FACTS = ExtractedFacts()


def _unique_strings(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def _unique_amounts(values: tuple[float, ...] | list[float]) -> tuple[float, ...]:
    amounts: list[float] = []
    for value in values:
        number = float(value)
        if isfinite(number) and number >= 0 and number not in amounts:
            amounts.append(number)
    return tuple(amounts)


def extract_rule_facts(
    request: AnalyzeTicketRequest,
    case_type: CaseType,
    safety_flags: list[str] | None = None,
) -> FactExtractionResult:
    """Extract deterministic facts from the complaint text."""

    transaction_ids = _unique_strings(extract_transaction_ids(request.complaint))
    amounts = _unique_amounts(extract_amounts(request.complaint))
    phones = _unique_strings(extract_phone_numbers(request.complaint))
    approximate_hour = extract_approximate_hour(request.complaint)
    flags = _unique_strings(safety_flags or [])

    reason_codes: list[str] = []
    confidence = 0.35
    if transaction_ids:
        confidence += 0.35
        reason_codes.append("rule_fact_transaction_id")
    if amounts:
        confidence += 0.25
        reason_codes.append("rule_fact_amount")
    if phones:
        confidence += 0.10
        reason_codes.append("rule_fact_phone")
    if approximate_hour is not None:
        confidence += 0.05
        reason_codes.append("rule_fact_time")
    if case_type != CaseType.OTHER:
        confidence += 0.15
        reason_codes.append("rule_case_hint")
    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        confidence = max(confidence, 0.95)
        reason_codes.append("rule_safety_case")

    return FactExtractionResult(
        facts=ExtractedFacts(
            transaction_ids=transaction_ids,
            amounts=amounts,
            phones=phones,
            approximate_hour=approximate_hour,
            safety_flags=flags,
        ),
        confidence=min(1.0, confidence),
        reason_codes=tuple(reason_codes),
        source="rules",
    )


def merge_facts(
    rule_result: FactExtractionResult,
    ai_result: FactExtractionResult | None,
) -> FactExtractionResult:
    """Merge AI facts conservatively, filling only facts rules missed."""

    if ai_result is None:
        return rule_result

    rule_facts = rule_result.facts
    ai_facts = ai_result.facts
    merged = ExtractedFacts(
        transaction_ids=(
            rule_facts.transaction_ids
            if rule_facts.transaction_ids
            else _unique_strings(ai_facts.transaction_ids)
        ),
        amounts=(
            rule_facts.amounts
            if rule_facts.amounts
            else _unique_amounts(ai_facts.amounts)
        ),
        phones=(
            rule_facts.phones
            if rule_facts.phones
            else _unique_strings(ai_facts.phones)
        ),
        approximate_hour=(
            rule_facts.approximate_hour
            if rule_facts.approximate_hour is not None
            else ai_facts.approximate_hour
        ),
        safety_flags=_unique_strings(list(rule_facts.safety_flags) + list(ai_facts.safety_flags)),
    )
    return FactExtractionResult(
        facts=merged,
        confidence=max(rule_result.confidence, ai_result.confidence),
        reason_codes=tuple(rule_result.reason_codes + ai_result.reason_codes),
        source="merged",
    )
