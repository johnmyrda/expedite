"""Event domain and persistence models."""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from expedite.models.event_catalog_price import EventCatalogPrice
    from expedite.models.order import OrderRecord


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
    orders: list["OrderRecord"] = Relationship(
        back_populates="event",
        cascade_delete=True,
    )
    catalog_prices: list["EventCatalogPrice"] = Relationship(
        back_populates="event",
        cascade_delete=True,
    )
