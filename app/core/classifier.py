"""Complaint case-type classifier with safety-first precedence."""

from dataclasses import dataclass

from app.schemas.enums import CaseType, Channel, UserType
from app.schemas.models import AnalyzeTicketRequest
from app.utils.text import has_any


@dataclass(frozen=True)
class ClassificationResult:
    case_type: CaseType
    reason_codes: list[str]


PHISHING_KEYWORDS = (
    "otp", "one time password", "pin", "password", "secret code", "fake call",
    "scam", "phishing", "suspicious sms", "suspicious call", "fraud", "account blocked",
    "ওটিপি", "পিন", "পাসওয়ার্ড", "পাসওয়ার্ড", "গোপন কোড", "ভুয়া কল", "ভুয়া কল",
    "প্রতার", "স্ক্যাম", "সন্দেহজনক", "ব্লক",
)
DUPLICATE_KEYWORDS = (
    "duplicate", "twice", "two times", "double charged", "deducted twice", "same payment",
    "দুই বার", "দুবার", "ডাবল", "দ্বিগুণ", "দুইবার কেটে",
)
WRONG_TRANSFER_KEYWORDS = (
    "wrong number", "wrong person", "wrong recipient", "mistakenly sent", "sent to wrong",
    "sent by mistake", "receiver not responding", "reverse it", "wrong account",
    "ভুল নম্বর", "ভুল করে", "ভুল ব্যক্ত", "ভুল রিসিভার", "ভুল প্রাপক", "ভুলে পাঠ",
    "ফেরত দিন", "রিভার্স",
)
SETTLEMENT_KEYWORDS = (
    "settlement", "sales not settled", "settlement delay", "merchant payout",
    "সেটেলমেন্ট", "বিক্রির টাকা", "পেমেন্ট সেটেল",
)
CASH_IN_KEYWORDS = (
    "cash in", "cash-in", "deposit not reflected", "balance not updated", "agent deposit",
    "ক্যাশ ইন", "ক্যাশইন", "জমা", "ব্যালেন্স আপডেট", "এজেন্ট",
)
PAYMENT_FAILED_KEYWORDS = (
    "payment failed", "failed but deducted", "balance deducted", "recharge failed", "app showed failed",
    "money cut", "payment unsuccessful", "failed payment", "টাকা কেটে", "পেমেন্ট ব্যর্থ",
    "রিচার্জ ব্যর্থ", "ফেইল",
)
REFUND_KEYWORDS = (
    "refund", "money back", "return my money", "changed my mind", "do not want product",
    "merchant refund", "ফেরত", "রিফান্ড", "টাকা ফেরত", "পণ্য চাই না",
)


def classify_case(request: AnalyzeTicketRequest) -> ClassificationResult:
    """Classify the complaint, prioritizing credential and scam reports."""
    complaint = request.complaint
    if has_any(complaint, PHISHING_KEYWORDS):
        return ClassificationResult(CaseType.PHISHING_OR_SOCIAL_ENGINEERING, ["phishing_or_social_engineering"])
    if has_any(complaint, DUPLICATE_KEYWORDS):
        return ClassificationResult(CaseType.DUPLICATE_PAYMENT, ["duplicate_payment_claim"])
    if has_any(complaint, WRONG_TRANSFER_KEYWORDS):
        return ClassificationResult(CaseType.WRONG_TRANSFER, ["wrong_transfer_claim"])
    if (
        has_any(complaint, SETTLEMENT_KEYWORDS)
        or (request.user_type == UserType.MERCHANT and has_any(complaint, ("pending", "not received", "delay")))
        or (request.channel == Channel.MERCHANT_PORTAL and has_any(complaint, ("pending", "settled", "sales")))
    ):
        return ClassificationResult(CaseType.MERCHANT_SETTLEMENT_DELAY, ["merchant_settlement_claim"])
    if has_any(complaint, CASH_IN_KEYWORDS):
        return ClassificationResult(CaseType.AGENT_CASH_IN_ISSUE, ["agent_cash_in_claim"])
    if has_any(complaint, PAYMENT_FAILED_KEYWORDS):
        return ClassificationResult(CaseType.PAYMENT_FAILED, ["payment_failed_claim"])
    if has_any(complaint, REFUND_KEYWORDS):
        return ClassificationResult(CaseType.REFUND_REQUEST, ["refund_request"])
    return ClassificationResult(CaseType.OTHER, ["insufficient_complaint_detail"])
