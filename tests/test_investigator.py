"""End-to-end /analyze-ticket happy path + safety filter behavior."""

from __future__ import annotations

from app.schemas import (
    CaseType,
    Department,
    EvidenceVerdict,
    Severity,
)
from app.services.ai_service import Narrative
from app.utils.safety import sanitize


def test_analyze_ticket_returns_exact_12_fields(client, sample_payload) -> None:
    r = client.post("/analyze-ticket", json=sample_payload)
    assert r.status_code == 200
    body = r.json()
    expected = {
        "ticket_id", "relevant_transaction_id", "evidence_verdict", "case_type",
        "severity", "department", "agent_summary", "recommended_next_action",
        "customer_reply", "human_review_required", "confidence", "reason_codes",
    }
    assert set(body.keys()) == expected
    assert body["ticket_id"] == sample_payload["ticket_id"]
    # Stub rule engine picks the first transaction in history.
    assert body["relevant_transaction_id"] == "TX1001"
    assert body["evidence_verdict"] in {e.value for e in EvidenceVerdict}
    assert body["case_type"] in {c.value for c in CaseType}
    assert body["severity"] in {s.value for s in Severity}
    assert body["department"] in {d.value for d in Department}
    assert 0.0 <= body["confidence"] <= 1.0


def test_safety_filter_strips_otp_request() -> None:
    bad = Narrative(
        agent_summary="Please share your OTP with us to verify.",
        recommended_next_action="Send OTP.",
        customer_reply="Kindly share your OTP.",
    )
    safe, repaired = sanitize(bad)
    assert repaired is True
    # The fallback text *warns* about OTP ("do not share any OTP") — that is
    # safe messaging, not a request. We verify the request language is gone.
    assert "share your OTP" not in safe.customer_reply
    assert "Send OTP." not in safe.recommended_next_action
    assert "do not share" in safe.customer_reply.lower()


def test_safety_filter_strips_refund_promise() -> None:
    bad = Narrative(
        agent_summary="Case reviewed.",
        recommended_next_action="Refund will be processed.",
        customer_reply="Your refund has been approved.",
    )
    safe, repaired = sanitize(bad)
    assert repaired is True
    assert "refund" not in safe.customer_reply.lower()


def test_safety_filter_passes_safe_text() -> None:
    good = Narrative(
        agent_summary="Case reviewed.",
        recommended_next_action="Escalate to dispute resolution.",
        customer_reply="An agent will contact you shortly.",
    )
    safe, repaired = sanitize(good)
    assert repaired is False
    assert safe == good


def test_safety_filter_strips_third_party_link() -> None:
    bad = Narrative(
        agent_summary="Case reviewed.",
        recommended_next_action="Contact +1 555 123 4567.",
        customer_reply="Please visit https://example.com/help.",
    )
    safe, repaired = sanitize(bad)
    assert repaired is True