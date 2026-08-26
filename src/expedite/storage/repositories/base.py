"""Generic SQLModel repository operations."""

from typing import Generic, TypeVar

from sqlmodel import Session, SQLModel

ModelT = TypeVar("ModelT", bound=SQLModel)


class Repository(Generic[ModelT]):
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
