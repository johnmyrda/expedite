from datetime import datetime
from pathlib import Path

from expedite.models import Event, Order
from expedite.storage.csv_store import order_csv_row


def test_order_csv_row_normalizes_valid_phone_to_e164(tmp_path: Path) -> None:
    event = Event(
        name="Test Event",
        start_date="2026-08-08",
        path=tmp_path,
        created_at=datetime.now(),
    )
    order = Order.model_construct(
        order_id=1,
        timestamp=datetime.now(),
        name="Jane",
        phone="(650) 253-0000",
        work_request="Thing",
        cost="12.50",
        event=event,
    )

    assert order_csv_row(order)["phone"] == "+16502530000"


def test_order_csv_row_preserves_invalid_phone(tmp_path: Path) -> None:
    event = Event(
        name="Test Event",
        start_date="2026-08-08",
        path=tmp_path,
        created_at=datetime.now(),
    )
    order = Order.model_construct(
        order_id=1,
        timestamp=datetime.now(),
        name="Jane",
        phone="123",
        work_request="Thing",
        cost="12.50",
        event=event,
    )

    assert order_csv_row(order)["phone"] == "123"
