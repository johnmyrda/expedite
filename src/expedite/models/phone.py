"""Phone-number validation and normalization."""

import phonenumbers
from phonenumbers import PhoneNumberFormat


def normalize_phone(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Phone number must be text.")

    try:
        number = phonenumbers.parse(value.strip(), "US")
    except phonenumbers.NumberParseException as error:
        raise ValueError(str(error)) from error

    reason = phonenumbers.is_possible_number_with_reason(number)
    if reason != phonenumbers.ValidationResult.IS_POSSIBLE:
        message = phonenumbers.ValidationResult.to_string(reason).replace("_", " ").lower()
        raise ValueError(f"Phone number is {message}.")

    if not phonenumbers.is_valid_number(number):
        raise ValueError("Phone number is not a valid US number.")

    return phonenumbers.format_number(number, PhoneNumberFormat.E164)


def normalize_phone_for_storage(value: object) -> str:
    try:
        return normalize_phone(value)
    except ValueError:
        return str(value or "")
