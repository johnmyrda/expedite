"""Application-wide SQLite persistence using SQLModel."""

from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from expedite.config import data_dir
from expedite.models import (
    Event,
    EventRecord,
    Order,
    OrderRecord,
    normalize_phone_for_storage,
)

DATABASE_FILENAME = "expedite.sqlite3"

def app_db_path() -> Path:
    return data_dir() / DATABASE_FILENAME


def orders_db_path(event: Event) -> Path:
    return app_db_path()


def _engine() -> Engine:
    data_dir().mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{app_db_path()}")


def _session() -> Session:
    engine = _engine()
    _migrate_folder_name_schema(engine)
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _table_columns(engine: Engine, table_name: str) -> set[str]:
    with engine.connect() as connection:
        rows = connection.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]) for row in rows}


def _migrate_folder_name_schema(engine: Engine) -> None:
    """Migrate the earlier schema that keyed orders by event folder name."""

    event_columns = _table_columns(engine, "events")
    order_columns = _table_columns(engine, "orders")
    if (not event_columns or "id" in event_columns) and (
        not order_columns or "event_id" in order_columns
    ):
        return

    with engine.begin() as connection:
        if event_columns and "id" not in event_columns:
            connection.exec_driver_sql("ALTER TABLE events RENAME TO events_legacy_folder_name")
        if order_columns and "event_id" not in order_columns:
            connection.exec_driver_sql("ALTER TABLE orders RENAME TO orders_legacy_folder_name")

    SQLModel.metadata.create_all(engine)

    with engine.begin() as connection:
        legacy_events = _table_columns(engine, "events_legacy_folder_name")
        if legacy_events:
            connection.exec_driver_sql(
                """
                INSERT OR IGNORE INTO events (folder_name, name, start_date, created_at)
                SELECT folder_name, name, start_date, created_at
                FROM events_legacy_folder_name
                """
            )
            connection.exec_driver_sql("DROP TABLE events_legacy_folder_name")

        legacy_orders = _table_columns(engine, "orders_legacy_folder_name")
        if legacy_orders:
            connection.exec_driver_sql(
                """
                INSERT OR IGNORE INTO orders (
                    event_id, order_id, timestamp, name, phone, work_request, cost, label_filename
                )
                SELECT
                    events.id,
                    legacy.order_id,
                    legacy.timestamp,
                    legacy.name,
                    legacy.phone,
                    legacy.work_request,
                    legacy.cost,
                    legacy.label_filename
                FROM orders_legacy_folder_name AS legacy
                JOIN events ON events.folder_name = legacy.event_folder_name
                """
            )
            connection.exec_driver_sql("DROP TABLE orders_legacy_folder_name")


def _ensure_aware(value: datetime) -> datetime:
    return value.astimezone()


def _event_from_record(record: EventRecord) -> Event:
    return Event(
        name=record.name,
        start_date=record.start_date,
        path=data_dir() / record.folder_name,
        created_at=_ensure_aware(record.created_at),
    )


def _event_record_by_folder(session: Session, folder_name: str) -> EventRecord | None:
    return session.exec(
        select(EventRecord).where(EventRecord.folder_name == folder_name)
    ).first()


def _ensure_event_record(session: Session, event: Event) -> EventRecord:
    record = _event_record_by_folder(session, event.folder_name())
    if record is None:
        record = EventRecord(
            folder_name=event.folder_name(),
            name=event.name,
            start_date=event.start_date,
            created_at=event.created_at,
        )
    else:
        record.name = event.name
        record.start_date = event.start_date
        record.created_at = event.created_at

    session.add(record)
    session.flush()
    return record


def save_event(event: Event) -> None:
    with _session() as session:
        _ensure_event_record(session, event)
        session.commit()


def get_event_metadata(event_path: Path) -> Event | None:
    with _session() as session:
        record = _event_record_by_folder(session, event_path.name)
    if record is None:
        return None
    return _event_from_record(record)


def list_event_metadata() -> list[Event]:
    data_dir().mkdir(parents=True, exist_ok=True)
    with _session() as session:
        records = session.exec(select(EventRecord)).all()
    return sorted(
        [_event_from_record(record) for record in records],
        key=lambda event: event.created_at,
        reverse=True,
    )


def list_order_records(event: Event) -> list[OrderRecord]:
    with _session() as session:
        event_record = _event_record_by_folder(session, event.folder_name())
        if event_record is None or event_record.id is None:
            return []
        records = session.exec(
            select(OrderRecord).where(OrderRecord.event_id == event_record.id)
        ).all()
    return sorted(records, key=lambda record: record.order_id)


def _order_from_record(event: Event, record: OrderRecord) -> Order:
    return Order.model_construct(
        order_id=record.order_id,
        timestamp=_ensure_aware(record.timestamp),
        name=record.name,
        phone=record.phone,
        work_request=record.work_request,
        cost=record.cost,
        event=event,
        label_filename=record.label_filename or None,
    )


def get_order(event: Event, order_id: int) -> Order | None:
    with _session() as session:
        event_record = _event_record_by_folder(session, event.folder_name())
        if event_record is None or event_record.id is None:
            return None
        record = session.exec(
            select(OrderRecord).where(
                OrderRecord.event_id == event_record.id,
                OrderRecord.order_id == order_id,
            )
        ).first()
    if record is None:
        return None
    return _order_from_record(event, record)


def _order_record(order: Order, event_id: int) -> OrderRecord:
    return OrderRecord(
        event_id=event_id,
        order_id=order.order_id,
        timestamp=_ensure_aware(order.timestamp),
        name=order.name,
        phone=normalize_phone_for_storage(order.phone),
        work_request=order.work_request,
        cost=order.cost,
        label_filename=order.label_filename or "",
    )


def append_order(order: Order) -> None:
    with _session() as session:
        event_record = _ensure_event_record(session, order.event)
        if event_record.id is None:
            raise RuntimeError("Event ID was not created before saving order.")
        session.add(_order_record(order, event_record.id))
        session.commit()


def update_order(order: Order) -> None:
    with _session() as session:
        event_record = _ensure_event_record(session, order.event)
        if event_record.id is None:
            raise RuntimeError("Event ID was not created before saving order.")
        session.merge(_order_record(order, event_record.id))
        session.commit()


def next_order_id(event: Event) -> int:
    with _session() as session:
        event_record = _event_record_by_folder(session, event.folder_name())
        if event_record is None or event_record.id is None:
            return 1
        records = session.exec(
            select(OrderRecord.order_id).where(OrderRecord.event_id == event_record.id)
        ).all()
    return max(records, default=0) + 1
