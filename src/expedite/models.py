"""Core domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated

import phonenumbers
from phonenumbers import PhoneNumberFormat
from phonenumbers.phonenumber import PhoneNumber
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
)


def _normalize_cost_value(value: object) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, str):
        return value.strip().replace("$", "").replace(",", "")
    if isinstance(value, int | float):
        return str(value)
    return ""


def _parse_cost(value: object) -> str:
    normalized = _normalize_cost_value(value)
    try:
        amount = Decimal(normalized)
    except (InvalidOperation, ValueError) as error:
        raise ValueError("Cost is not parseable as a number.") from error

    if amount.is_zero():
        raise ValueError("Cost is $0.")
    return normalized


def _validated_phone_number(value: object) -> PhoneNumber:
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

    return number


def normalize_phone(value: object) -> str:
    return phonenumbers.format_number(_validated_phone_number(value), PhoneNumberFormat.E164)


def normalize_phone_for_csv(value: object) -> str:
    try:
        return normalize_phone(value)
    except ValueError:
        return str(value or "")


@dataclass(frozen=True)
class Message:
    text: str


class Event(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    start_date: str
    path: Path
    created_at: datetime

    def folder_name(self) -> str:
        return self.path.name


class Order(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_id: int
    timestamp: datetime = Field(default_factory=datetime.now)
    name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=2),
        Message("Names are usually longer"),
    ]
    phone: Annotated[str, BeforeValidator(normalize_phone)]
    work_request: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    cost: Annotated[str, BeforeValidator(_parse_cost)]
    event: Event
    label_filename: str | None = None

    @classmethod
    def from_csv_row(cls, event: Event, row: dict[str, object]) -> Order:
        return cls.model_validate({**row, "event": event})

    def with_label_filename(self, label_filename: str) -> Order:
        return self.model_copy(update={"label_filename": label_filename})
