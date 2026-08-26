"""Event repository."""

from sqlmodel import Session, select

from expedite.models import EventRecord
from expedite.storage.repositories.base import Repository


class EventRepository(Repository[EventRecord]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, EventRecord)

    def find_by_folder_name(self, folder_name: str) -> EventRecord | None:
        return self.session.exec(
            select(EventRecord).where(EventRecord.folder_name == folder_name)
        ).first()

    def find_all(self) -> list[EventRecord]:
        return list(self.session.exec(select(EventRecord)).all())
