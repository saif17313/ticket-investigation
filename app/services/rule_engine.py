"""Rule-engine interface.

The backend owns the *contract* the rule engine must satisfy, but not the
implementation. The rule-engine teammate fills in :class:`RuleEngine` with
real heuristics; meanwhile :class:`StubRuleEngine` keeps the API runnable
end-to-end with conservative defaults.

The contract is intentionally narrow: one input (``AnalyzeRequest``) and
one output (:class:`InvestigationDecision`). Anything beyond that — caching,
state, telemetry — belongs inside the implementation, not the interface.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models import InvestigationDecision
from app.schemas import AnalyzeRequest, CaseType, Department, EvidenceVerdict, Severity
from app.schemas.response import EvidenceVerdict as _EV
from app.schemas.response import Severity as _SEV
from app.schemas.response import CaseType as _CT
from app.schemas.response import Department as _DEPT


@runtime_checkable
class RuleEngine(Protocol):
    """Contract every rule-engine implementation must satisfy."""

    def decide(self, request: AnalyzeRequest) -> InvestigationDecision:
        """Return the deterministic investigation decision for ``request``."""
        ...


class StubRuleEngine:
    """Conservative fallback used until the real rule engine is plugged in.

    Behavior:
        - If a matching transaction is present, mark evidence ``consistent``
          and route to dispute resolution.
        - Otherwise mark evidence ``insufficient_data`` and require human
          review.

    This guarantees the API never invents evidence while the real engine is
    being built.
    """

    def decide(self, request: AnalyzeRequest) -> InvestigationDecision:
        if request.transaction_history:
            relevant = request.transaction_history[0]
            return InvestigationDecision(
                relevant_transaction_id=relevant.transaction_id,
                evidence_verdict=EvidenceVerdict.CONSISTENT,
                case_type=CaseType.WRONG_TRANSFER,
                severity=Severity.MEDIUM,
                department=Department.DISPUTE_RESOLUTION,
                human_review_required=True,
                confidence=0.5,
                reason_codes=["STUB_RULE_ENGINE"],
            )
        return InvestigationDecision(
            relevant_transaction_id=None,
            evidence_verdict=EvidenceVerdict.INSUFFICIENT_DATA,
            case_type=CaseType.OTHER,
            severity=Severity.MEDIUM,
            department=Department.CUSTOMER_SUPPORT,
            human_review_required=True,
            confidence=0.2,
            reason_codes=["STUB_RULE_ENGINE_NO_HISTORY"],
        )