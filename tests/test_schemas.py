"""Schema and enum allow-list tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    AnalyzeResponse,
    CaseType,
    Department,
    EvidenceVerdict,
    Severity,
)
from app.schemas.request import AnalyzeRequest, TransactionIn


def test_response_has_exact_12_fields() -> None:
    """The spec lists exactly 12 fields. Anything else is a violation."""

    resp = AnalyzeResponse(
        ticket_id="t",
        relevant_transaction_id=None,
        evidence_verdict=EvidenceVerdict.INSUFFICIENT_DATA,
        case_type=CaseType.OTHER,
        severity=Severity.LOW,
        department=Department.CUSTOMER_SUPPORT,
        agent_summary="a",
        recommended_next_action="b",
        customer_reply="c",
        human_review_required=False,
        confidence=0.1,
        reason_codes=[],
    )
    expected = {
        "ticket_id",
        "relevant_transaction_id",
        "evidence_verdict",
        "case_type",
        "severity",
        "department",
        "agent_summary",
        "recommended_next_action",
        "customer_reply",
        "human_review_required",
        "confidence",
        "reason_codes",
    }
    assert set(resp.model_dump().keys()) == expected


def test_invalid_enum_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AnalyzeResponse(
            ticket_id="t",
            relevant_transaction_id=None,
            evidence_verdict="maybe",  # type: ignore[arg-type]
            case_type="other",
            severity="low",
            department="customer_support",
            agent_summary="a",
            recommended_next_action="b",
            customer_reply="c",
            human_review_required=False,
            confidence=0.1,
        )


def test_request_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate({
            "ticket_id": "t",
            "complaint": "x",
            "language": "en",
            "channel": "app",
            "user_type": "retail",
            "campaign_context": "",
            "transaction_history": [],
            "metadata": {},
            "extra_field": "not allowed",
        })


def test_transaction_in_field_names_are_locked() -> None:
    tx = TransactionIn(
        transaction_id="X",
        timestamp="t",
        type="transfer",
        amount=1.0,
        counterparty="c",
        status="completed",
    )
    assert tx.transaction_id == "X"
    assert tx.amount == 1.0