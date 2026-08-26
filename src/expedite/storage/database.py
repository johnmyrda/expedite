"""SQLite engine, schema, session, and transaction management."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.pool import ConnectionPoolEntry
from sqlmodel import Session, SQLModel, create_engine

from expedite.config import data_dir

DATABASE_FILENAME = "expedite.sqlite3"

_ENGINE: Engine | None = None
_ENGINE_PATH: Path | None = None
_ENGINE_LOCK = Lock()


def app_db_path() -> Path:
    return data_dir() / DATABASE_FILENAME


def _enable_sqlite_foreign_keys(
    dbapi_connection: DBAPIConnection,
    _: ConnectionPoolEntry,
) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def _create_engine(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")
    sqlalchemy_event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    SQLModel.metadata.create_all(engine)
    return engine


def engine() -> Engine:
    global _ENGINE, _ENGINE_PATH

    path = app_db_path()
    with _ENGINE_LOCK:
        if _ENGINE is None or path != _ENGINE_PATH:
            if _ENGINE is not None:
                _ENGINE.dispose()
            _ENGINE = _create_engine(path)
            _ENGINE_PATH = path
        return _ENGINE


def open_session() -> Session:
    return Session(engine())


@contextmanager
def transaction() -> Iterator[Session]:
    with open_session() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def dispose_engine() -> None:
    global _ENGINE, _ENGINE_PATH

    with _ENGINE_LOCK:
        if _ENGINE is not None:
            _ENGINE.dispose()
        _ENGINE = None
        _ENGINE_PATH = None
