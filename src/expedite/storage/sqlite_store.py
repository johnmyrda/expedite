"""Application-wide SQLite persistence using SQLModel."""

from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from expedite.config import data_dir
from expedite.models import (
    CatalogItem,
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
    SQLModel.metadata.create_all(engine)
    return Session(engine)


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


def list_catalog_items() -> list[CatalogItem]:
    with _session() as session:
        items = session.exec(select(CatalogItem)).all()
    return sorted(items, key=lambda item: item.name.casefold())


def save_catalog_item(
    *,
    item_id: int | None,
    name: str,
    description: str | None,
    base_price_cents: int,
    active: bool,
) -> CatalogItem:
    now = datetime.now().astimezone()
    with _session() as session:
        item = session.get(CatalogItem, item_id) if item_id is not None else None
        if item_id is not None and item is None:
            raise ValueError(f"Catalog item {item_id} does not exist.")
        if item is None:
            item = CatalogItem(
                name=name,
                description=description,
                base_price_cents=base_price_cents,
                active=active,
                created_at=now,
                updated_at=now,
            )
        else:
            item.name = name
            item.description = description
            item.base_price_cents = base_price_cents
            item.active = active
            item.updated_at = now
        session.add(item)
        session.commit()
        session.refresh(item)
        session.expunge(item)
    return item


def list_order_records(event: Event) -> list[OrderRecord]:
    with _session() as session:
        event_record = _event_record_by_folder(session, event.folder_name())
        if event_record is None:
            return []
        records = list(event_record.orders)
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
        if event_record is None:
            return None
        record = next(
            (order for order in event_record.orders if order.order_id == order_id),
            None,
        )
    if record is None:
        return None
    return _order_from_record(event, record)


def _order_record(order: Order) -> OrderRecord:
    return OrderRecord(
        order_id=order.order_id,
        timestamp=_ensure_aware(order.timestamp),
        name=order.name,
        phone=normalize_phone_for_storage(order.phone),
        work_request=order.work_request,
        cost=order.cost,
        label_filename=order.label_filename,
    )


def append_order(order: Order) -> None:
    with _session() as session:
        event_record = _ensure_event_record(session, order.event)
        event_record.orders.append(_order_record(order))
        session.add(event_record)
        session.commit()


def update_order(order: Order) -> None:
    with _session() as session:
        event_record = _ensure_event_record(session, order.event)
        existing_order = next(
            (record for record in event_record.orders if record.order_id == order.order_id),
            None,
        )
        if existing_order is None:
            event_record.orders.append(_order_record(order))
        else:
            replacement = _order_record(order)
            existing_order.timestamp = replacement.timestamp
            existing_order.name = replacement.name
            existing_order.phone = replacement.phone
            existing_order.work_request = replacement.work_request
            existing_order.cost = replacement.cost
            existing_order.label_filename = replacement.label_filename
        session.add(event_record)
        session.commit()


def next_order_id(event: Event) -> int:
    with _session() as session:
        event_record = _event_record_by_folder(session, event.folder_name())
        if event_record is None:
            return 1
        records = [order.order_id for order in event_record.orders]
    return max(records, default=0) + 1
