"""Pydantic models for the public QueueStorm API."""

from datetime import datetime
from math import isfinite
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.enums import (
    CaseType,
    Channel,
    Department,
    EvidenceVerdict,
    Language,
    Severity,
    TransactionStatus,
    TransactionType,
    UserType,
)


class TransactionHistoryItem(BaseModel):
    """A possibly partial transaction supplied as supporting evidence."""

    model_config = ConfigDict(extra="ignore")

    transaction_id: str | None = None
    timestamp: datetime | None = None
    type: TransactionType | None = None
    amount: float | None = None
    counterparty: str | None = None
    status: TransactionStatus | None = None

    @field_validator("transaction_id", "counterparty", mode="before")
    @classmethod
    def strip_optional_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: float | None) -> float | None:
        if value is not None and (not isfinite(value) or value < 0):
            raise ValueError("amount must be a finite non-negative number")
        return value


class AnalyzeTicketRequest(BaseModel):
    """Validated request accepted by POST /analyze-ticket."""

    model_config = ConfigDict(extra="ignore")

    ticket_id: str = Field(...)
    complaint: str = Field(...)
    language: Language | None = None
    channel: Channel | None = None
    user_type: UserType | None = None
    campaign_context: str | None = None
    transaction_history: list[TransactionHistoryItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("ticket_id", "complaint")
    @classmethod
    def require_non_blank_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @field_validator("campaign_context", mode="before")
    @classmethod
    def normalize_campaign_context(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value


class AnalyzeTicketResponse(BaseModel):
    """Exact successful response shape returned by the API."""

    ticket_id: str
    relevant_transaction_id: str | None
    evidence_verdict: EvidenceVerdict
    case_type: CaseType
    severity: Severity
    department: Department
    agent_summary: str
    recommended_next_action: str
    customer_reply: str
    human_review_required: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason_codes: list[str]


class ErrorResponse(BaseModel):
    """Non-sensitive error shape for invalid requests and unexpected failures."""

    detail: str
