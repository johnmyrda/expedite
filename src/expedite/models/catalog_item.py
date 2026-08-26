"""Catalog item persistence model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from expedite.models.event_catalog_price import EventCatalogPrice
    from expedite.models.order import OrderLineRecord


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
    event_prices: list["EventCatalogPrice"] = Relationship(back_populates="catalog_item")
    order_lines: list["OrderLineRecord"] = Relationship(back_populates="catalog_item")
