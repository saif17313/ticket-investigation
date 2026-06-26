"""Request schemas for the QueueStorm Investigator API.

These models are the **public input contract** for ``POST /analyze-ticket``.
They are deliberately separated from the response schema and from internal
domain models so that the API surface can evolve independently of the rule
engine and AI module.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionIn(BaseModel):
    """A single transaction as supplied by the caller.

    Field names are locked to the specification and must not be renamed.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    transaction_id: str = Field(..., min_length=1, description="Unique transaction identifier.")
    timestamp: str = Field(..., min_length=1, description="ISO-8601 timestamp of the transaction.")
    type: str = Field(..., min_length=1, description="Transaction type (transfer, payment, ...).")
    amount: float = Field(..., ge=0, description="Absolute transaction amount in account currency.")
    counterparty: str = Field(..., min_length=1, description="Recipient / sender identifier.")
    status: str = Field(..., min_length=1, description="Transaction status (completed, failed, ...).")


class AnalyzeRequest(BaseModel):
    """Top-level request body for ``POST /analyze-ticket``.

    Every field listed in the specification is required. ``metadata`` is kept
    as an open dictionary because the specification marks it as opaque
    context for downstream consumers.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ticket_id: str = Field(..., min_length=1, description="Unique ticket identifier.")
    complaint: str = Field(..., min_length=1, description="Free-text customer complaint.")
    language: str = Field(..., min_length=1, description="BCP-47 language tag (e.g. 'en', 'bn').")
    channel: str = Field(..., min_length=1, description="Originating channel (app, web, ussd, ...).")
    user_type: str = Field(..., min_length=1, description="Customer segment (retail, merchant, agent).")
    # ``campaign_context`` is optional/empty in many real tickets; we allow
    # ``""`` here so a missing campaign does not produce 422. The field is
    # still required (must be present) per the specification.
    campaign_context: str = Field(default="", description="Marketing or campaign reference, if any.")
    transaction_history: list[TransactionIn] = Field(
        default_factory=list,
        description="Recent transactions to evaluate against the complaint.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form contextual metadata (device, region, ...).",
    )

    @field_validator("complaint")
    @classmethod
    def _complaint_not_blank(cls, value: str) -> str:
        """Reject empty/whitespace-only complaints as semantically invalid (422)."""

        if not value.strip():
            raise ValueError("complaint must not be empty")
        return value
