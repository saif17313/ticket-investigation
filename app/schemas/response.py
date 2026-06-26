"""Response schemas for the QueueStorm Investigator API.

The :class:`AnalyzeResponse` model is the **public output contract** for
``POST /analyze-ticket``. Field names, order, and enum values are frozen by
the specification and must never be changed without an explicit spec update.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# --- Enums (exact value sets from the specification) -------------------------


class EvidenceVerdict(str, Enum):
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"
    INSUFFICIENT_DATA = "insufficient_data"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseType(str, Enum):
    WRONG_TRANSFER = "wrong_transfer"
    PAYMENT_FAILED = "payment_failed"
    REFUND_REQUEST = "refund_request"
    DUPLICATE_PAYMENT = "duplicate_payment"
    MERCHANT_SETTLEMENT_DELAY = "merchant_settlement_delay"
    AGENT_CASH_IN_ISSUE = "agent_cash_in_issue"
    PHISHING_OR_SOCIAL_ENGINEERING = "phishing_or_social_engineering"
    OTHER = "other"


class Department(str, Enum):
    CUSTOMER_SUPPORT = "customer_support"
    DISPUTE_RESOLUTION = "dispute_resolution"
    PAYMENTS_OPS = "payments_ops"
    MERCHANT_OPERATIONS = "merchant_operations"
    AGENT_OPERATIONS = "agent_operations"
    FRAUD_RISK = "fraud_risk"


# --- Response model ----------------------------------------------------------


class AnalyzeResponse(BaseModel):
    """Structured investigation result returned by ``POST /analyze-ticket``.

    Field order matches the specification exactly. ``extra='forbid'`` and
    strict typing ensure any drift between the rule engine output and this
    contract fails loudly during development.
    """

    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(..., description="Echoed ticket identifier from the request.")
    relevant_transaction_id: str | None = Field(
        ...,
        description="ID of the transaction the complaint refers to, or null if none.",
    )
    evidence_verdict: EvidenceVerdict = Field(..., description="Evidence verdict enum.")
    case_type: CaseType = Field(..., description="Classified case type.")
    severity: Severity = Field(..., description="Severity assessment.")
    department: Department = Field(..., description="Routing department.")
    agent_summary: str = Field(..., min_length=1, description="Concise summary for the agent.")
    recommended_next_action: str = Field(..., min_length=1, description="Recommended next action.")
    customer_reply: str = Field(..., min_length=1, description="Safe customer-facing reply.")
    human_review_required: bool = Field(..., description="Whether a human must review the case.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score in [0, 1].")
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Machine-readable reason codes produced by the rule engine.",
    )
