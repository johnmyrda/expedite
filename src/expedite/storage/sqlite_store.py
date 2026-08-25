"""Application-wide SQLite persistence using SQLModel."""

import csv
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from expedite.config import data_dir
from expedite.models import (
    CatalogItem,
    Event,
    EventCatalogPrice,
    EventRecord,
    Order,
    OrderLine,
    OrderLineItem,
    OrderRecord,
    normalize_phone_for_storage,
)

DATABASE_FILENAME = "expedite.sqlite3"
ORDERS_CSV_FILENAME = "orders.csv"
ORDER_EXPORT_COLUMNS = (
    "order_number",
    "timestamp",
    "customer_name",
    "phone",
    "line_items",
    "order_total",
    "label_filename",
)


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


def event_catalog_prices(event: Event) -> dict[int, int]:
    with _session() as session:
        event_record = _event_record_by_folder(session, event.folder_name())
        if event_record is None:
            return {}
        prices = list(event_record.catalog_prices)
    return {
        price.catalog_item_id: price.price_cents
        for price in prices
        if price.catalog_item_id is not None
    }


def save_event_catalog_price(
    event: Event,
    catalog_item_id: int,
    price_cents: int | None,
) -> None:
    if price_cents is not None and price_cents < 0:
        raise ValueError("Event price must be zero or greater.")

    with _session() as session:
        event_record = _ensure_event_record(session, event)
        if event_record.id is None:
            raise RuntimeError("Event ID was not created before saving event price.")
        if session.get(CatalogItem, catalog_item_id) is None:
            raise ValueError(f"Catalog item {catalog_item_id} does not exist.")

        key = (event_record.id, catalog_item_id)
        price = session.get(EventCatalogPrice, key)
        if price_cents is None:
            if price is not None:
                session.delete(price)
        elif price is None:
            session.add(
                EventCatalogPrice(
                    event_id=event_record.id,
                    catalog_item_id=catalog_item_id,
                    price_cents=price_cents,
                )
            )
        else:
            price.price_cents = price_cents
            session.add(price)
        session.commit()


def list_order_records(event: Event) -> list[OrderRecord]:
    with _session() as session:
        event_record = _event_record_by_folder(session, event.folder_name())
        if event_record is None:
            return []
        records = list(event_record.orders)
    return sorted(records, key=lambda record: record.order_id)


def _order_from_record(event: Event, record: OrderRecord) -> Order:
    line_items = [
        OrderLineItem(
            line_number=line.line_number,
            catalog_item_id=line.catalog_item_id,
            description=line.description,
            quantity=line.quantity,
            unit_price_cents=line.unit_price_cents,
            notes=line.notes,
        )
        for line in sorted(record.line_items, key=lambda line: line.line_number)
    ]
    return Order.model_construct(
        order_id=record.order_id,
        timestamp=_ensure_aware(record.timestamp),
        name=record.name,
        phone=record.phone,
        work_request=record.work_request,
        cost=record.cost,
        event=event,
        label_filename=record.label_filename or None,
        line_items=line_items,
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


def _order_line_record(line: OrderLineItem) -> OrderLine:
    return OrderLine(
        line_number=line.line_number,
        catalog_item_id=line.catalog_item_id,
        description=line.description,
        quantity=line.quantity,
        unit_price_cents=line.unit_price_cents,
        notes=line.notes,
    )


def export_orders_csv(event: Event) -> Path:
    with _session() as session:
        event_record = _event_record_by_folder(session, event.folder_name())
        records = (
            sorted(event_record.orders, key=lambda record: record.order_id)
            if event_record is not None
            else []
        )
        orders = [_order_from_record(event, record) for record in records]

    event.path.mkdir(parents=True, exist_ok=True)
    output_path = event.path / ORDERS_CSV_FILENAME
    temporary_path = output_path.with_suffix(".csv.tmp")
    with temporary_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=ORDER_EXPORT_COLUMNS)
        writer.writeheader()
        for order in orders:
            line_items = []
            for line in order.line_items:
                summary = (
                    f"{line.quantity} x {line.description} @ "
                    f"{line.unit_price_cents / 100:.2f}"
                )
                if line.notes:
                    summary = f"{summary} ({line.notes})"
                line_items.append(summary)
            writer.writerow(
                {
                    "order_number": order.order_id,
                    "timestamp": order.timestamp.isoformat(timespec="minutes"),
                    "customer_name": order.name,
                    "phone": order.phone,
                    "line_items": "; ".join(line_items) or order.work_request,
                    "order_total": order.cost,
                    "label_filename": order.label_filename or "",
                }
            )
    temporary_path.replace(output_path)
    return output_path


def append_order(order: Order) -> None:
    with _session() as session:
        event_record = _ensure_event_record(session, order.event)
        order_record = _order_record(order)
        order_record.line_items = [_order_line_record(line) for line in order.line_items]
        event_record.orders.append(order_record)
        session.add(event_record)
        session.commit()
    export_orders_csv(order.event)


def update_order(order: Order) -> None:
    with _session() as session:
        event_record = _ensure_event_record(session, order.event)
        existing_order = next(
            (record for record in event_record.orders if record.order_id == order.order_id),
            None,
        )
        if existing_order is None:
            replacement = _order_record(order)
            replacement.line_items = [
                _order_line_record(line) for line in order.line_items
            ]
            event_record.orders.append(replacement)
        else:
            replacement = _order_record(order)
            existing_order.timestamp = replacement.timestamp
            existing_order.name = replacement.name
            existing_order.phone = replacement.phone
            existing_order.work_request = replacement.work_request
            existing_order.cost = replacement.cost
            existing_order.label_filename = replacement.label_filename
            for line in list(existing_order.line_items):
                session.delete(line)
            session.flush()
            existing_order.line_items = [
                _order_line_record(line) for line in order.line_items
            ]
        session.add(event_record)
        session.commit()
    export_orders_csv(order.event)


def next_order_id(event: Event) -> int:
    with _session() as session:
        event_record = _event_record_by_folder(session, event.folder_name())
        if event_record is None:
            return 1
        records = [order.order_id for order in event_record.orders]
    return max(records, default=0) + 1
