"""Core domain models."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated

import phonenumbers
from phonenumbers import PhoneNumberFormat
from pydantic import BeforeValidator, StringConstraints
from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def _parse_cost(value: object) -> str:
    if isinstance(value, str):
        normalized = value.strip().replace("$", "").replace(",", "")
    elif isinstance(value, Decimal | int | float):
        normalized = str(value)
    else:
        normalized = ""

    try:
        amount = Decimal(normalized)
    except (InvalidOperation, ValueError) as error:
        raise ValueError("Cost is not parseable as a number.") from error

    if amount.is_zero():
        raise ValueError("Cost is $0.")
    return normalized


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


@dataclass(frozen=True)
class Message:
    text: str


class EventBase(SQLModel):
    name: str = Field(index=True)
    start_date: str = Field(index=True)
    created_at: datetime = Field(index=True)


class Event(EventBase):
    path: Path

    def folder_name(self) -> str:
        return self.path.name


class EventRecord(EventBase, table=True):
    __tablename__ = "events"

    id: int | None = Field(default=None, primary_key=True)
    folder_name: str = Field(index=True, unique=True)
    orders: list["OrderRecord"] = Relationship(back_populates="event")
    catalog_prices: list["EventCatalogPrice"] = Relationship(back_populates="event")


class CatalogItem(SQLModel, table=True):
    __tablename__ = "catalog"
    __table_args__ = (CheckConstraint("base_price_cents >= 0"),)

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None
    base_price_cents: int
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    event_prices: list["EventCatalogPrice"] = Relationship(
        back_populates="catalog_item"
    )
    order_lines: list["OrderLine"] = Relationship(back_populates="catalog_item")


class OrderBase(SQLModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=2),
        Message("Names are usually longer"),
    ]
    phone: Annotated[str, BeforeValidator(normalize_phone)]
    work_request: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    cost: Annotated[str, BeforeValidator(_parse_cost)]
    label_filename: str | None = None


class OrderLineBase(SQLModel):
    line_number: int
    description: str
    quantity: int = 1
    unit_price_cents: int
    notes: str | None = None


class OrderLineItem(OrderLineBase):
    catalog_item_id: int | None = None


class Order(OrderBase):
    order_id: int
    event: Event
    line_items: list[OrderLineItem] = Field(default_factory=list)


class OrderRecord(OrderBase, table=True):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("event_id", "order_number"),)

    id: int | None = Field(default=None, primary_key=True)
    event_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("events.id"), nullable=False, index=True),
    )
    order_id: int = Field(
        sa_column=Column("order_number", Integer, nullable=False)
    )
    event: EventRecord | None = Relationship(back_populates="orders")
    line_items: list["OrderLine"] = Relationship(back_populates="order")


class EventCatalogPrice(SQLModel, table=True):
    __tablename__ = "event_catalog_prices"
    __table_args__ = (CheckConstraint("price_cents >= 0"),)

    event_id: int = Field(primary_key=True, foreign_key="events.id")
    catalog_item_id: int = Field(primary_key=True, foreign_key="catalog.id")
    price_cents: int
    event: EventRecord | None = Relationship(back_populates="catalog_prices")
    catalog_item: CatalogItem | None = Relationship(back_populates="event_prices")


class OrderLine(OrderLineBase, table=True):
    __tablename__ = "order_lines"
    __table_args__ = (
        UniqueConstraint("order_id", "line_number"),
        CheckConstraint("line_number > 0"),
        CheckConstraint("quantity > 0"),
        CheckConstraint("unit_price_cents >= 0"),
    )

    id: int | None = Field(default=None, primary_key=True)
    order_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("orders.id"), nullable=False, index=True),
    )
    catalog_item_id: int | None = Field(default=None, foreign_key="catalog.id")
    order: OrderRecord | None = Relationship(back_populates="line_items")
    catalog_item: CatalogItem | None = Relationship(back_populates="order_lines")
