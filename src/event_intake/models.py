"""Core domain models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Any, TypeAlias

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
)
from pydantic_extra_types.phone_numbers import PhoneNumberValidator


def _parse_cost(value: Any) -> Decimal:
    if isinstance(value, str):
        value = value.strip().replace("$", "").replace(",", "")
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as error:
        raise ValueError("Cost is not parseable as a number.") from error


def _reject_zero_cost(value: Decimal) -> Decimal:
    if value.is_zero():
        raise ValueError("Cost is $0.")
    return value


CostForWarning: TypeAlias = Annotated[
    Decimal,
    BeforeValidator(_parse_cost),
    AfterValidator(_reject_zero_cost),
]


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
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2)]
    phone: Annotated[
        str,
        PhoneNumberValidator(default_region="US"),
    ]
    work_request: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    cost: Annotated[
        str,
        BeforeValidator(_parse_cost),
        AfterValidator(_reject_zero_cost),
    ]
    event: Event
    label_filename: str | None = None

    @classmethod
    def from_csv_row(cls, event: Event, row: dict[str, Any]) -> Order:
        return cls.model_validate({**row, "event": event})

    def with_label_filename(self, label_filename: str) -> Order:
        return self.model_copy(update={"label_filename": label_filename})
