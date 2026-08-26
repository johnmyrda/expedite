"""Event-specific catalog price persistence model."""

from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel

from expedite.models.catalog_item import CatalogItem
from expedite.models.event import EventRecord


class EventCatalogPrice(SQLModel, table=True):
    __tablename__ = "event_catalog_prices"
    __table_args__ = (CheckConstraint("price_cents >= 0"),)

    event_id: int = Field(primary_key=True, foreign_key="events.id")
    catalog_item_id: int = Field(primary_key=True, foreign_key="catalog.id")
    price_cents: int
    event: EventRecord | None = Relationship(back_populates="catalog_prices")
    catalog_item: CatalogItem | None = Relationship(back_populates="event_prices")
