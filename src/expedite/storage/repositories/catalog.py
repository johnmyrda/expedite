"""Catalog repositories."""

from sqlmodel import Session, select

from expedite.models import CatalogItem, EventCatalogPrice
from expedite.storage.repositories.base import Repository


class CatalogRepository(Repository[CatalogItem]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, CatalogItem)

    def find_all(self) -> list[CatalogItem]:
        return list(self.session.exec(select(CatalogItem)).all())


class EventCatalogPriceRepository(Repository[EventCatalogPrice]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, EventCatalogPrice)

    def find_all_by_event_id(self, event_id: int) -> list[EventCatalogPrice]:
        return list(
            self.session.exec(
                select(EventCatalogPrice).where(EventCatalogPrice.event_id == event_id)
            ).all()
        )
