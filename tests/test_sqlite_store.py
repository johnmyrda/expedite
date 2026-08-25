import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from expedite.models import Event, Order
from expedite.storage.sqlite_store import (
    app_db_path,
    append_order,
    get_event_metadata,
    get_order,
    list_order_records,
    next_order_id,
    orders_db_path,
    save_event,
    update_order,
)


@pytest.fixture(autouse=True)
def _data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVENT_INTAKE_DATA_DIR", str(tmp_path))


def _event(tmp_path: Path) -> Event:
    event_path = tmp_path / "test_event"
    event_path.mkdir()
    return Event(
        name="Test Event",
        start_date="2026-08-08",
        path=event_path,
        created_at=datetime.now().astimezone(),
    )


def test_event_metadata_is_saved_to_sqlite(tmp_path: Path) -> None:
    event = _event(tmp_path)

    save_event(event)
    loaded_event = get_event_metadata(event.path)

    assert loaded_event == event
    assert not (event.path / "event.json").exists()


def test_schema_uses_event_ids_indexes_and_order_foreign_key(tmp_path: Path) -> None:
    event = _event(tmp_path)
    save_event(event)

    with sqlite3.connect(app_db_path()) as connection:
        event_columns = {
            row[1]: row for row in connection.execute("PRAGMA table_info(events)").fetchall()
        }
        order_columns = {
            row[1]: row for row in connection.execute("PRAGMA table_info(orders)").fetchall()
        }
        catalog_columns = {
            row[1]: row for row in connection.execute("PRAGMA table_info(catalog)").fetchall()
        }
        event_price_columns = {
            row[1]: row
            for row in connection.execute(
                "PRAGMA table_info(event_catalog_prices)"
            ).fetchall()
        }
        order_line_columns = {
            row[1]: row
            for row in connection.execute("PRAGMA table_info(order_lines)").fetchall()
        }
        event_indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(events)").fetchall()
        }
        order_foreign_keys = connection.execute("PRAGMA foreign_key_list(orders)").fetchall()

    assert "id" in event_columns
    assert "folder_name" in event_columns
    assert "id" in order_columns
    assert "event_id" in order_columns
    assert "order_number" in order_columns
    assert "order_id" not in order_columns
    assert "event_folder_name" not in order_columns
    assert {"id", "name", "base_price_cents", "active"} <= catalog_columns.keys()
    assert {"event_id", "catalog_item_id", "price_cents"} <= event_price_columns.keys()
    assert {
        "id",
        "order_id",
        "catalog_item_id",
        "description",
        "quantity",
        "unit_price_cents",
    } <= order_line_columns.keys()
    assert any("folder_name" in index for index in event_indexes)
    assert any(
        row[2] == "events" and row[3] == "event_id" and row[4] == "id"
        for row in order_foreign_keys
    )


def test_sqlite_store_appends_reads_and_updates_orders(tmp_path: Path) -> None:
    event = _event(tmp_path)
    timestamp = datetime.now().astimezone()
    order = Order.model_construct(
        order_id=next_order_id(event),
        timestamp=timestamp,
        name="Jane",
        phone="(650) 253-0000",
        work_request="Original",
        cost="12.50",
        event=event,
        label_filename="old.png",
    )

    append_order(order)

    assert orders_db_path(event).exists()
    assert next_order_id(event) == 2
    assert list_order_records(event)[0].phone == "+16502530000"

    saved = get_order(event, 1)
    assert saved is not None
    assert saved.work_request == "Original"

    update_order(saved.model_copy(update={"work_request": "Updated", "label_filename": "new.png"}))

    orders = list_order_records(event)
    assert len(orders) == 1
    assert orders[0].work_request == "Updated"
    assert orders[0].label_filename == "new.png"
