"""Order and line-item domain and persistence models."""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Optional

from pydantic import BeforeValidator, StringConstraints
from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from expedite.models.event import Event, EventRecord
from expedite.models.phone import normalize_phone
from expedite.money import parse_money_amount

if TYPE_CHECKING:
    from expedite.models.catalog_item import CatalogItem


"""Custom validation-message metadata."""


@dataclass(frozen=True)
class Message:
    text: str


def _parse_cost(value: object) -> str:
    try:
        amount = parse_money_amount(value)
    except ValueError as error:
        raise ValueError("Cost is not parseable as a number.") from error
    if amount.is_zero():
        raise ValueError("Cost is $0.")
    return format(amount, "f")


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


class OrderLine(SQLModel):
    line_number: int
    description: str
    quantity: int = 1
    unit_price_cents: int
    notes: str | None = None
    catalog_item_id: int | None = None


class Order(OrderBase):
    order_id: int
    event: Event
    line_items: list[OrderLine] = Field(default_factory=list)


class OrderRecord(OrderBase, table=True):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("event_id", "order_number"),)

    id: int | None = Field(default=None, primary_key=True)
    event_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("events.id"), nullable=False, index=True),
    )
    order_id: int = Field(sa_column=Column("order_number", Integer, nullable=False))
    event: EventRecord | None = Relationship(back_populates="orders")
    line_items: list["OrderLineRecord"] = Relationship(back_populates="order")


class OrderLineRecord(OrderLine, table=True):
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
    catalog_item: Optional["CatalogItem"] = Relationship(back_populates="order_lines")
