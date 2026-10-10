"""Generic SQLModel repository operations."""

from sqlmodel import Session, SQLModel


class Repository[ModelT: SQLModel]:
    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    def get(self, identity: object) -> ModelT | None:
        return self.session.get(self.model, identity)

    def save(self, record: ModelT) -> ModelT:
        self.session.add(record)
        self.session.flush()
        return record

    def delete(self, record: ModelT) -> None:
        self.session.delete(record)
