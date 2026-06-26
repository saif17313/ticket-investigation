"""Internal domain models.

These are **not** part of the API surface. They exist so that the rule engine
and the AI module can exchange strongly-typed data without depending on the
public Pydantic schemas. Anything returned to the client must be assembled
into :class:`app.schemas.AnalyzeResponse` at the API boundary.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.response import CaseType, Department, EvidenceVerdict, Severity


class InvestigationDecision(BaseModel):
    """Result of the rule engine's reasoning over one ticket.

    This model deliberately mirrors the deterministic fields of the public
    response. The AI module will later add the three narrative fields to
    produce the final :class:`AnalyzeResponse`.
    """

    model_config = ConfigDict(extra="forbid")

    relevant_transaction_id: str | None = Field(
        default=None,
        description="ID of the matched transaction, or None when no match.",
    )
    evidence_verdict: EvidenceVerdict = Field(..., description="Evidence verdict.")
    case_type: CaseType = Field(..., description="Classified case type.")
    severity: Severity = Field(..., description="Severity assessment.")
    department: Department = Field(..., description="Routing department.")
    human_review_required: bool = Field(..., description="Whether human review is required.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score in [0, 1].")
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Machine-readable reason codes.",
    )
