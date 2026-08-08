"""Non-blocking intake-field validation messages."""

import re
from decimal import Decimal, InvalidOperation


def validate_name(value: str | None) -> str | None:
    if len((value or "").strip()) <= 1:
        return "Name is empty or only one character."
    return None


def validate_phone(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 10 or (len(digits) == 11 and digits.startswith("1")):
        return None
    return "Phone number should contain 10 digits, or 11 digits starting with 1."


def validate_work_request(value: str | None) -> str | None:
    if not (value or "").strip():
        return "Work Request is empty."
    return None


def validate_cost(value: str | None) -> str | None:
    try:
        amount = Decimal((value or "").strip().replace("$", "").replace(",", ""))
    except (InvalidOperation, ValueError):
        return "Cost is not parseable as a number."

    if amount.is_zero():
        return "Cost is $0."
    return None
