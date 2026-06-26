"""Final guardrail that prevents unsafe generated text from leaving the service."""

from __future__ import annotations

import re

from app.schemas.models import AnalyzeTicketResponse

SENSITIVE_REQUEST_PATTERN = re.compile(
    r"(?<!do not )\b(?:send|provide|share|enter|tell(?:\s+us)?)\s+(?:your\s+)?(?:otp|pin|password|secret code|full card number)\b",
    flags=re.IGNORECASE,
)
UNSAFE_PROMISE_PATTERN = re.compile(
    r"\b(?:we will refund(?: you)?|we will reverse|guaranteed refund|your account will be unblocked|we will unblock your account|guaranteed account recovery)\b",
    flags=re.IGNORECASE,
)
THIRD_PARTY_PATTERN = re.compile(
    r"\b(?:contact|call|message)\s+(?:the caller|that number|the sender|this person)\b",
    flags=re.IGNORECASE,
)


def _unsafe(value: str) -> bool:
    return bool(
        SENSITIVE_REQUEST_PATTERN.search(value)
        or UNSAFE_PROMISE_PATTERN.search(value)
        or THIRD_PARTY_PATTERN.search(value)
    )


def _reply_fallback(bangla: bool) -> str:
    if bangla:
        return "আপনার অনুরোধটি নথিভুক্ত করা হয়েছে। PIN, OTP, পাসওয়ার্ড, গোপন কোড বা সম্পূর্ণ কার্ড নম্বর কারও সঙ্গে শেয়ার করবেন না। আমাদের সহায়তা দল অফিসিয়াল চ্যানেলের মাধ্যমে বিষয়টি পর্যালোচনা করবে।"
    return "We have received your report. Please do not share your PIN, OTP, password, secret code, or full card number with anyone. Our support team will review the case through official channels."


def enforce_safety(response: AnalyzeTicketResponse, bangla: bool = False) -> AnalyzeTicketResponse:
    """Replace unsafe free text and reassert output invariants before returning JSON."""
    summary = response.agent_summary
    action = response.recommended_next_action
    reply = response.customer_reply
    if _unsafe(summary):
        summary = "Case has been classified using the available transaction evidence."
    if _unsafe(action):
        action = "Review the available details through the applicable official support workflow."
    if _unsafe(reply):
        reply = _reply_fallback(bangla)

    reason_codes = [str(code) for code in response.reason_codes if isinstance(code, str) and code]
    return response.model_copy(
        update={
            "agent_summary": summary,
            "recommended_next_action": action,
            "customer_reply": reply,
            "confidence": min(1.0, max(0.0, float(response.confidence))),
            "reason_codes": reason_codes or ["safe_fallback"],
        }
    )
