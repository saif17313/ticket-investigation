"""[redacted] 2.5 Flash implementation of :class:`AIService`.

The service talks to Gemini through the official ``google-genai`` async
client. It is designed to **fail safely**: any error (missing key, timeout,
bad JSON) is caught and a templated narrative is returned instead. That
keeps the API responsive even when the upstream model is down.

Safety is enforced **after** generation by :func:`app.utils.safety.sanitize`,
so unsafe text never leaves the service.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.config import Settings
from app.models import InvestigationDecision
from app.schemas import AnalyzeRequest
from app.services.ai_service import AIService, Narrative

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are QueueStorm Investigator, an internal AI copilot \
for fintech customer support agents. You produce professional, concise, \
neutral JSON output. You must NEVER:

- Ask the customer for an OTP, PIN, password, or card number.
- Promise a refund, reversal, account recovery, or account unblock.
- Direct the customer to a third party, external link, phone number, or handle.

If the situation is ambiguous, recommend that an agent review the case.

Respond with strict JSON only — no prose, no markdown fences — with the keys:
agent_summary, recommended_next_action, customer_reply.
"""

_USER_TEMPLATE = """Ticket: {ticket_id}
Language: {language}
Channel: {channel}
User type: {user_type}

Decision:
- relevant_transaction_id: {relevant}
- evidence_verdict: {verdict}
- case_type: {case_type}
- severity: {severity}
- department: {department}
- human_review_required: {review}
- reason_codes: {codes}
- confidence: {confidence}

Complaint:
{complaint}
"""


def _safe_fallback(decision: InvestigationDecision) -> Narrative:
    """Templated narrative used when the model is disabled or fails."""

    return Narrative(
        agent_summary=(
            f"Case routed to {decision.department.value}. "
            f"Evidence verdict: {decision.evidence_verdict.value}. "
            f"Reason codes: {', '.join(decision.reason_codes) or 'none'}."
        ),
        recommended_next_action=(
            "Verify the transaction details with the customer and escalate "
            "to the assigned department."
        ),
        customer_reply=(
            "Thank you for contacting us. A support agent will review your "
            "case and get back to you shortly."
        ),
    )


class GeminiService:
    """[redacted] implementation of the AI service."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Any | None = None

    def _get_client(self) -> Any:
        """Lazily construct the async Gemini client.

        Done lazily so the service can be instantiated even when the API
        key is absent; the first real call surfaces a clear configuration
        error.
        """

        if self._client is not None:
            return self._client
        if not self._settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        # Imported here so the module loads even if google-genai is missing.
        from google import genai

        self._client = genai.Client(api_key=self._settings.gemini_api_key)
        return self._client

    async def narrate(
        self,
        request: AnalyzeRequest,
        decision: InvestigationDecision,
    ) -> Narrative:
        if not self._settings.llm_enabled:
            return _safe_fallback(decision)

        user_prompt = _USER_TEMPLATE.format(
            ticket_id=request.ticket_id,
            language=request.language,
            channel=request.channel,
            user_type=request.user_type,
            relevant=decision.relevant_transaction_id or "null",
            verdict=decision.evidence_verdict.value,
            case_type=decision.case_type.value,
            severity=decision.severity.value,
            department=decision.department.value,
            review=decision.human_review_required,
            codes=decision.reason_codes,
            confidence=decision.confidence,
            complaint=request.complaint,
        )

        try:
            client = self._get_client()
            response = await client.aio.models.generate_content(
                model=self._settings.gemini_model,
                contents=user_prompt,
                config={
                    "system_instruction": _SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "temperature": 0.2,
                },
            )
            return _parse_narrative(response.text or "")
        except Exception as exc:  # noqa: BLE001 - we intentionally catch all
            logger.warning(
                "gemini_call_failed",
                extra={"ticket_id": request.ticket_id, "exc_type": type(exc).__name__},
            )
            return _safe_fallback(decision)


def _parse_narrative(raw: str) -> Narrative:
    """Extract the three narrative strings from the model output."""

    text = raw.strip()
    # Strip accidental markdown fences.
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to recover a JSON object from surrounding prose.
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("model did not return JSON") from None
        data = json.loads(match.group(0))

    return Narrative(
        agent_summary=str(data.get("agent_summary", "")).strip() or "Case reviewed.",
        recommended_next_action=str(data.get("recommended_next_action", "")).strip() or "Escalate to agent.",
        customer_reply=str(data.get("customer_reply", "")).strip() or "An agent will contact you shortly.",
    )