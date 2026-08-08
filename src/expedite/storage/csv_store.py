"""CSV persistence for orders."""

import csv
from pathlib import Path

from expedite.models import Event, Order


def order_csv_fieldnames() -> list[str]:
    return [field_name for field_name in Order.model_fields if field_name != "event"]


def orders_csv_path(event: Event) -> Path:
    return event.path / "orders.csv"


def append_order(order: Order) -> None:
    path = orders_csv_path(order.event)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()

    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=order_csv_fieldnames())
        if is_new:
            writer.writeheader()
        writer.writerow(order.model_dump(mode="json", exclude={"event"}))


def next_order_id(event: Event) -> int:
    path = orders_csv_path(event)
    if not path.exists():
        return 1

    highest = 0
    with path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                order_id = int(row.get("order_id", "0"))
            except ValueError:
                continue
            highest = max(highest, order_id)
    return highest + 1
