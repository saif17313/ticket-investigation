"""Final guardrail that prevents unsafe generated text from leaving the service."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.models import AnalyzeTicketResponse

INPUT_CREDENTIAL_OR_SCAM_PATTERN = re.compile(
    r"\b(?:otp|one[-\s]?time password|pin|password|secret code|cvv|cvc|card\s*(?:number|no)|fake call|scam|phishing|fraud|suspicious)\b",
    flags=re.IGNORECASE,
)
PROMPT_INJECTION_PATTERN = re.compile(
    r"\b(?:ignore previous|ignore all previous|disregard instructions|system prompt|developer message|override rules|jailbreak|return only|follow my instruction)\b",
    flags=re.IGNORECASE,
)
SENSITIVE_REQUEST_PATTERN = re.compile(
    r"(?<!do not )\b(?:send|provide|share|enter|submit|confirm|tell(?:\s+us)?)\s+(?:your\s+)?(?:otp|pin|password|secret code|card\s*(?:number|no)|full card number|cvv|cvc)\b",
    flags=re.IGNORECASE,
)
UNSAFE_PROMISE_PATTERN = re.compile(
    r"\b(?:we will refund(?: you)?|we will reverse|guaranteed refund|refund\s+(?:has been|will be)\s+(?:approved|processed|initiated)|your account will be unblocked|we will unblock your account|account recovery is guaranteed|guaranteed account recovery)\b",
    flags=re.IGNORECASE,
)
THIRD_PARTY_PATTERN = re.compile(
    r"(?:https?://[^\s]+|@[A-Za-z0-9_]{3,}|\b(?:contact|call|message|whatsapp|telegram)\s+(?:the caller|that number|the sender|this person|[+\d][\d\s\-]{6,}))\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class InputSafetyScan:
    """Safety flags found before financial classification."""

    force_phishing: bool
    prompt_injection: bool
    reason_codes: list[str]


def scan_input_safety(value: str | None) -> InputSafetyScan:
    """Detect safety and prompt-injection signals in the complaint text."""

    text = value or ""
    reason_codes: list[str] = []
    force_phishing = False
    if INPUT_CREDENTIAL_OR_SCAM_PATTERN.search(text):
        force_phishing = True
        reason_codes.append("input_safety_credential_or_scam")
    prompt_injection = bool(PROMPT_INJECTION_PATTERN.search(text))
    if prompt_injection:
        reason_codes.append("input_prompt_injection")
    return InputSafetyScan(
        force_phishing=force_phishing,
        prompt_injection=prompt_injection,
        reason_codes=reason_codes,
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
    repaired = False
    if _unsafe(summary):
        summary = "Case has been classified using the available transaction evidence."
        repaired = True
    if _unsafe(action):
        action = "Review the available details through the applicable official support workflow."
        repaired = True
    if _unsafe(reply):
        reply = _reply_fallback(bangla)
        repaired = True

    reason_codes = [str(code) for code in response.reason_codes if isinstance(code, str) and code]
    if repaired:
        reason_codes.append("output_safety_repaired")
    return response.model_copy(
        update={
            "agent_summary": summary,
            "recommended_next_action": action,
            "customer_reply": reply,
            "human_review_required": response.human_review_required or repaired,
            "confidence": min(1.0, max(0.0, float(response.confidence))),
            "reason_codes": reason_codes or ["safe_fallback"],
        }
    )
