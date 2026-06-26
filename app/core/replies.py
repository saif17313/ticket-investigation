"""Professional, policy-safe agent summaries and customer reply templates."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.evidence import EvidenceDecision
from app.schemas.enums import CaseType, Department, EvidenceVerdict, Severity
from app.schemas.models import AnalyzeTicketRequest
from app.utils.text import bangla_is_dominant, has_any


@dataclass(frozen=True)
class GeneratedTexts:
    agent_summary: str
    recommended_next_action: str
    customer_reply: str


def _use_bangla(request: AnalyzeTicketRequest) -> bool:
    if request.language is not None and request.language.value == "bn":
        return True
    if request.language is not None and request.language.value == "en":
        return False
    return bangla_is_dominant(request.complaint)


def _amount_text(evidence: EvidenceDecision) -> str:
    amount = evidence.relevant_transaction.amount if evidence.relevant_transaction else None
    if amount is None:
        return "the reported amount"
    return f"{amount:g} BDT"


def _transaction_text(evidence: EvidenceDecision) -> str:
    return evidence.relevant_transaction_id or "the reported transaction"


def _english_texts(
    request: AnalyzeTicketRequest,
    case_type: CaseType,
    evidence: EvidenceDecision,
    department: Department,
) -> GeneratedTexts:
    transaction_id = _transaction_text(evidence)
    amount = _amount_text(evidence)
    verdict = evidence.evidence_verdict

    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return GeneratedTexts(
            "Customer reports a suspected phishing or social-engineering attempt. No transaction evidence is required to begin fraud-risk review.",
            "Record the reported contact details if available and route the case to fraud-risk review through the official workflow.",
            "Thank you for reporting this. Please do not share your PIN, OTP, password, secret code, or full card number with anyone. Our support team will review the report through official channels.",
        )
    if case_type == CaseType.WRONG_TRANSFER:
        if verdict == EvidenceVerdict.CONSISTENT:
            return GeneratedTexts(
                f"Customer reports a possible wrong transfer of {amount} linked to {transaction_id}; available transaction evidence is consistent with the report.",
                f"Verify {transaction_id} details with the customer and start the wrong-transfer dispute review according to policy.",
                f"We have noted your concern about transaction {transaction_id}. Please do not share your PIN or OTP with anyone. Our dispute team will review the case through official support channels.",
            )
        if verdict == EvidenceVerdict.INCONSISTENT:
            return GeneratedTexts(
                f"Customer claims {transaction_id} was sent to the wrong recipient, but the available transaction history does not fully support that claim.",
                f"Flag {transaction_id} for human review and verify the recipient pattern with the customer before any dispute decision.",
                f"We have received your request regarding transaction {transaction_id}. Please do not share your PIN or OTP with anyone. Our dispute team will review the case carefully through official support channels.",
            )
        return GeneratedTexts(
            "Customer reports a possible wrong transfer, but the available history does not identify one transaction with enough confidence.",
            "Request only the transaction ID, amount, approximate time, and recipient number needed to identify the transaction.",
            "We need a little more information to identify the transaction. Please share the transaction ID, amount, approximate time, and recipient number only. Do not share your PIN, OTP, password, or secret code.",
        )
    if case_type == CaseType.PAYMENT_FAILED:
        return GeneratedTexts(
            f"Customer reports that {transaction_id} for {amount} failed and may have caused a balance deduction; evidence verdict is {verdict.value}.",
            f"Review {transaction_id} ledger status. If policy confirms an eligible failed-payment adjustment, process it through the standard official workflow.",
            f"We have noted that transaction {transaction_id} may have caused an unexpected balance deduction. Our payments team will review the case and any eligible amount will be returned through official channels. Please do not share your PIN or OTP with anyone.",
        )
    if case_type == CaseType.REFUND_REQUEST:
        return GeneratedTexts(
            f"Customer requests a refund related to {transaction_id}; available evidence verdict is {verdict.value}.",
            "Check the merchant refund policy and payment record, then explain the available official options to the customer.",
            "We have received your refund request. Our support team will review the merchant policy and transaction details. Any eligible amount will be returned through official channels; please do not share your PIN or OTP with anyone.",
        )
    if case_type == CaseType.DUPLICATE_PAYMENT:
        return GeneratedTexts(
            f"Transaction history indicates a possible duplicate payment, with {transaction_id} identified as the later suspected duplicate.",
            f"Review the duplicate-payment evidence for {transaction_id} and follow the payments dispute workflow.",
            f"We have noted a possible duplicate payment involving transaction {transaction_id}. Our payments team will review it, and any eligible amount will be returned through official channels. Please do not share your PIN or OTP with anyone.",
        )
    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        return GeneratedTexts(
            f"Merchant reports a delayed settlement; {transaction_id} is the most relevant available settlement record and the evidence verdict is {verdict.value}.",
            f"Review settlement status for {transaction_id} and provide the merchant with the applicable processing update through the official workflow.",
            f"We have recorded your settlement concern for {transaction_id}. Our merchant operations team will review the settlement status and update you through official support channels.",
        )
    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        return GeneratedTexts(
            f"Customer reports an agent cash-in issue; {transaction_id} is the relevant available record and the evidence verdict is {verdict.value}.",
            f"Review agent and ledger records for {transaction_id} and escalate through the agent-operations workflow.",
            f"আপনার ক্যাশ-ইন সংক্রান্ত অনুরোধটি নথিভুক্ত করা হয়েছে। আমাদের এজেন্ট অপারেশনস টিম বিষয়টি অফিসিয়াল চ্যানেলের মাধ্যমে পর্যালোচনা করবে। কারও সঙ্গে PIN বা OTP শেয়ার করবেন না।",
        )
    return GeneratedTexts(
        "The complaint does not contain enough reliable detail to identify a specific support case or transaction.",
        "Request the transaction ID, amount, approximate time, and a short description of what happened before routing the case.",
        "We need a few more details to help. Please share the transaction ID, amount, approximate time, and what happened. Do not share your PIN, OTP, password, secret code, or full card number.",
    )


def _bangla_texts(
    case_type: CaseType,
    evidence: EvidenceDecision,
) -> GeneratedTexts:
    transaction_id = _transaction_text(evidence)
    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        return GeneratedTexts(
            f"গ্রাহক ক্যাশ-ইন ব্যালেন্সে প্রতিফলিত না হওয়ার অভিযোগ করেছেন। প্রাসঙ্গিক রেকর্ড {transaction_id}; প্রমাণের ফলাফল {evidence.evidence_verdict.value}।",
            f"{transaction_id}–এর এজেন্ট ও লেজার রেকর্ড যাচাই করে এজেন্ট অপারেশনস প্রক্রিয়ায় পর্যালোচনার জন্য পাঠান।",
            f"আপনার ক্যাশ-ইন সংক্রান্ত অনুরোধটি নথিভুক্ত করা হয়েছে। {transaction_id}–এর তথ্য আমাদের এজেন্ট অপারেশনস টিম অফিসিয়াল চ্যানেলের মাধ্যমে পর্যালোচনা করবে। কারও সঙ্গে PIN, OTP, পাসওয়ার্ড বা গোপন কোড শেয়ার করবেন না।",
        )
    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return GeneratedTexts(
            "গ্রাহক সম্ভাব্য ফিশিং বা সামাজিক প্রকৌশল প্রতারণার অভিযোগ করেছেন।",
            "অফিসিয়াল ফ্রড-রিস্ক প্রক্রিয়ায় অভিযোগটি পর্যালোচনার জন্য পাঠান।",
            "এটি জানানোর জন্য ধন্যবাদ। কারও সঙ্গে PIN, OTP, পাসওয়ার্ড, গোপন কোড বা সম্পূর্ণ কার্ড নম্বর শেয়ার করবেন না। আমাদের সহায়তা দল অফিসিয়াল চ্যানেলের মাধ্যমে বিষয়টি পর্যালোচনা করবে।",
        )
    if case_type == CaseType.WRONG_TRANSFER and evidence.evidence_verdict == EvidenceVerdict.INSUFFICIENT_DATA:
        return GeneratedTexts(
            "সম্ভাব্য ভুল ট্রান্সফারের অভিযোগ পাওয়া গেছে, তবে একটি নির্দিষ্ট লেনদেন শনাক্ত করার মতো পর্যাপ্ত প্রমাণ নেই।",
            "শুধু ট্রানজেকশন আইডি, টাকার পরিমাণ, আনুমানিক সময় এবং প্রাপকের নম্বর চেয়ে নিন।",
            "লেনদেনটি শনাক্ত করতে আরও কিছু তথ্য দরকার। শুধু ট্রানজেকশন আইডি, টাকার পরিমাণ, আনুমানিক সময় ও প্রাপকের নম্বর দিন। PIN, OTP, পাসওয়ার্ড বা গোপন কোড শেয়ার করবেন না।",
        )
    # English templates remain clearer for mixed operational terminology; only a
    # native Bangla reply is mandatory for Bangla-dominant cases.
    return _english_texts_placeholder(case_type, evidence)


def _english_texts_placeholder(case_type: CaseType, evidence: EvidenceDecision) -> GeneratedTexts:
    """Safe generic fallback for Bangla cases without a dedicated template."""
    transaction_id = _transaction_text(evidence)
    return GeneratedTexts(
        f"Case classified as {case_type.value}; {transaction_id} is the relevant available transaction record.",
        "Review the available transaction evidence through the applicable official support workflow.",
        f"আপনার অনুরোধটি নথিভুক্ত করা হয়েছে। প্রাসঙ্গিক লেনদেন {transaction_id} অফিসিয়াল চ্যানেলের মাধ্যমে পর্যালোচনা করা হবে। PIN, OTP, পাসওয়ার্ড বা গোপন কোড শেয়ার করবেন না।",
    )


def generate_texts(
    request: AnalyzeTicketRequest,
    case_type: CaseType,
    evidence: EvidenceDecision,
    department: Department,
    severity: Severity,
) -> GeneratedTexts:
    """Return templates without using customer text as executable instructions."""
    # Department and severity remain part of the stable template interface for
    # future policy-specific wording, even though today's rules use case type.
    _ = severity
    if _use_bangla(request):
        return _bangla_texts(case_type, evidence)
    return _english_texts(request, case_type, evidence, department)
