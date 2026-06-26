"""Output safety filter for the AI module.

The safety rules from the specification are enforced as a last line of
defense — even if the AI produces unsafe text, it never reaches the
customer. The filter also flips ``human_review_required = True`` whenever
it repairs something, so a human still sees the case.
"""

from __future__ import annotations

import re
from dataclasses import replace

from app.services.ai_service import Narrative

# --- Patterns that must NEVER appear in customer-facing text ----------------

# Requests for sensitive credentials (OTP, PIN, password, card/CVV).
_SENSITIVE_REQUEST = re.compile(
    r"\b(otp|one[-\s]?time\s+password|pin|password|cvv|card\s*(?:number|no)?|"
    r"share\s+(?:your|the)\s+(?:otp|pin|password|card))\b",
    re.IGNORECASE,
)

# Promises of refund / reversal / account recovery / unblock.
_PROMISE_PATTERN = re.compile(
    r"\b(we\s+will\s+(?:refund|reverse|recover|unblock)|"
    r"refund\s+(?:has\s+been|will\s+be)\s+(?:processed|approved|initiated)|"
    r"your\s+(?:refund|reversal)\s+is\s+(?:confirmed|approved))\b",
    re.IGNORECASE,
)

# Third-party links or handles — agents must never direct customers to them.
_THIRD_PARTY = re.compile(
    r"(https?://(?![\w.-]*queuestorm)[^\s]+|@[A-Za-z0-9_]{3,}|"
    r"(?:contact|call|message)\s+[+\d][\d\s\-]{6,})",
    re.IGNORECASE,
)

_SAFE_FALLBACK = (
    "For your security, please do not share any OTP, PIN, password, or card "
    "number with anyone. A support agent will review your case and contact "
    "you through the official app."
)


def sanitize(narrative: Narrative) -> tuple[Narrative, bool]:
    """Return ``(safe_narrative, repaired)``.

    ``repaired`` is True when any field had to be replaced. Callers should
    set ``human_review_required = True`` whenever ``repaired`` is True.
    """

    repaired = False
    new_fields: dict[str, str] = {}

    for field_name in ("agent_summary", "recommended_next_action", "customer_reply"):
        text = getattr(narrative, field_name)
        if _SENSITIVE_REQUEST.search(text) or _PROMISE_PATTERN.search(text) or _THIRD_PARTY.search(text):
            new_fields[field_name] = _SAFE_FALLBACK
            repaired = True
        else:
            new_fields[field_name] = text

    if not repaired:
        return narrative, False
    return replace(narrative, **new_fields), True