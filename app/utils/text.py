"""Text normalization and lightweight English/Bangla extraction helpers."""

from __future__ import annotations

import re
import unicodedata

BENGALI_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def normalize_text(value: str | None) -> str:
    """Normalize digits, Unicode, whitespace, and case for rule matching."""
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value).translate(BENGALI_DIGITS)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def contains_bangla(value: str | None) -> bool:
    return bool(value and re.search(r"[\u0980-\u09ff]", value))


def bangla_is_dominant(value: str | None) -> bool:
    """Choose Bangla templates when Bangla script outweighs Latin letters."""
    if not value:
        return False
    bangla_count = len(re.findall(r"[\u0980-\u09ff]", value))
    latin_count = len(re.findall(r"[A-Za-z]", value))
    return bangla_count > 0 and bangla_count >= latin_count


def has_any(value: str | None, keywords: tuple[str, ...] | list[str]) -> bool:
    text = normalize_text(value)
    return any(normalize_text(keyword) in text for keyword in keywords)


def extract_amounts(value: str | None) -> list[float]:
    """Extract likely BDT amounts without mistaking phone numbers for money."""
    text = normalize_text(value)
    amounts: list[float] = []
    currency_patterns = (
        r"(?:৳)\s*(\d[\d,]*(?:\.\d+)?)",
        r"(?<!\d)(\d[\d,]*(?:\.\d+)?)\s*(?:taka|tk|bdt|টাকা)\b",
    )
    for pattern in currency_patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            number = float(match.replace(",", ""))
            if number not in amounts:
                amounts.append(number)

    if amounts:
        return amounts

    # A bare amount is common in short complaints. Keep plausible monetary values
    # and deliberately skip phone-length values, transaction IDs, and clock hours.
    for token in re.findall(r"(?<![a-z0-9-])(\d{3,7}(?:\.\d+)?)(?![a-z0-9-])", text):
        number = float(token)
        if number not in amounts:
            amounts.append(number)
    return amounts


def extract_transaction_ids(value: str | None) -> list[str]:
    """Extract explicit transaction identifiers such as TXN-9101."""
    text = normalize_text(value)
    pattern = r"\b(?:txn|tx|transaction)[-_]?[a-z0-9-]*\d[a-z0-9-]*\b"
    return [match.upper() for match in re.findall(pattern, text, flags=re.IGNORECASE)]


def extract_phone_numbers(value: str | None) -> list[str]:
    """Extract Bangladesh mobile numbers in local or +880 format."""
    text = normalize_text(value)
    matches = re.findall(r"(?<!\d)(?:\+?880|0)1\d{8,9}(?!\d)", text)
    return [normalize_phone(number) for number in matches]


def normalize_phone(value: str | None) -> str:
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("01") and len(digits) == 11:
        return f"880{digits[1:]}"
    if digits.startswith("8801"):
        return digits
    return digits


def extract_approximate_hour(value: str | None) -> int | None:
    """Extract an approximate local hour from common English and Bangla phrases."""
    text = normalize_text(value)
    match = re.search(r"\b(1[0-2]|0?[1-9])\s*(a\.?m\.?|p\.?m\.?)\b", text)
    if match:
        hour = int(match.group(1))
        meridiem = match.group(2).replace(".", "")
        if meridiem == "pm" and hour != 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        return hour

    period_hours = {
        "morning": 9,
        "সকাল": 9,
        "noon": 12,
        "দুপুর": 13,
        "afternoon": 15,
        "বিকাল": 16,
        "evening": 19,
        "সন্ধ্যা": 19,
        "night": 21,
        "রাত": 21,
    }
    return next((hour for phrase, hour in period_hours.items() if phrase in text), None)
