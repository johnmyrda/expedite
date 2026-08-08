"""CSV persistence for orders."""

import csv
from datetime import datetime
from pathlib import Path

from expedite.models import Event, Order


def order_csv_fieldnames() -> list[str]:
    return [field_name for field_name in Order.model_fields if field_name != "event"]


def orders_csv_path(event: Event) -> Path:
    return event.path / "orders.csv"


def read_order_rows(event: Event) -> list[dict[str, str]]:
    path = orders_csv_path(event)
    if not path.exists():
        return []

    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def order_from_row(event: Event, row: dict[str, str]) -> Order:
    timestamp_text = row.get("timestamp", "")
    try:
        timestamp = datetime.fromisoformat(timestamp_text)
    except ValueError:
        timestamp = datetime.now().astimezone()

    return Order.model_construct(
        order_id=int(row.get("order_id", "0")),
        timestamp=timestamp,
        name=row.get("name", ""),
        phone=row.get("phone", ""),
        work_request=row.get("work_request", ""),
        cost=row.get("cost", ""),
        event=event,
        label_filename=row.get("label_filename") or None,
    )


def get_order(event: Event, order_id: int) -> Order | None:
    for row in read_order_rows(event):
        try:
            row_order_id = int(row.get("order_id", "0"))
        except ValueError:
            continue
        if row_order_id == order_id:
            return order_from_row(event, row)
    return None


def append_order(order: Order) -> None:
    path = orders_csv_path(order.event)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()

    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=order_csv_fieldnames())
        if is_new:
            writer.writeheader()
        writer.writerow(order.model_dump(mode="json", exclude={"event"}))


def update_order(order: Order) -> None:
    path = orders_csv_path(order.event)
    rows = read_order_rows(order.event)
    replacement = order.model_dump(mode="json", exclude={"event"})
    updated = False

    for index, row in enumerate(rows):
        try:
            row_order_id = int(row.get("order_id", "0"))
        except ValueError:
            continue
        if row_order_id == order.order_id:
            rows[index] = {
                key: str(value) if value is not None else ""
                for key, value in replacement.items()
            }
            updated = True
            break

    if not updated:
        append_order(order)
        return

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=order_csv_fieldnames())
        writer.writeheader()
        writer.writerows(rows)


def next_order_id(event: Event) -> int:
    path = orders_csv_path(event)
    if not path.exists():
        return 1

    highest = 0
    for row in read_order_rows(event):
        try:
            order_id = int(row.get("order_id", "0"))
        except ValueError:
            continue
        highest = max(highest, order_id)
    return highest + 1
