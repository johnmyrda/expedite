import csv
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from expedite.models import Event, Order, OrderLine, OrderLineRecord
from expedite.storage.database import engine
from expedite.storage.sqlite_store import (
    _order_line_record,
    app_db_path,
    append_order,
    event_catalog_prices,
    get_event_metadata,
    get_order,
    list_catalog_items,
    list_order_records,
    next_order_id,
    orders_db_path,
    save_catalog_item,
    save_event,
    save_event_catalog_price,
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
            for row in connection.execute("PRAGMA table_info(event_catalog_prices)").fetchall()
        }
        order_line_columns = {
            row[1]: row for row in connection.execute("PRAGMA table_info(order_lines)").fetchall()
        }
        event_indexes = {
            row[1] for row in connection.execute("PRAGMA index_list(events)").fetchall()
        }
        order_foreign_keys = connection.execute("PRAGMA foreign_key_list(orders)").fetchall()
        order_line_foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(order_lines)"
        ).fetchall()

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
        row[2] == "events"
        and row[3] == "event_id"
        and row[4] == "id"
        and row[6] == "CASCADE"
        for row in order_foreign_keys
    )
    assert any(
        row[2] == "orders"
        and row[3] == "order_id"
        and row[4] == "id"
        and row[6] == "CASCADE"
        for row in order_line_foreign_keys
    )
    assert any(
        row[2] == "catalog"
        and row[3] == "catalog_item_id"
        and row[4] == "id"
        and row[6] == "SET NULL"
        for row in order_line_foreign_keys
    )


def test_sqlite_foreign_keys_are_enforced(tmp_path: Path) -> None:
    save_event(_event(tmp_path))

    with engine().connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        with pytest.raises(IntegrityError):
            connection.exec_driver_sql(
                """
                INSERT INTO order_lines (
                    order_id, line_number, description, quantity, unit_price_cents
                ) VALUES (999, 1, 'Orphan line', 1, 1000)
                """
            )


def test_catalog_items_can_be_created_and_updated() -> None:
    created = save_catalog_item(
        item_id=None,
        name="Stickbox Repair",
        description="Repair and calibrate one stickbox.",
        base_price_cents=2500,
        active=True,
    )

    assert created.id is not None
    assert list_catalog_items() == [created]

    updated = save_catalog_item(
        item_id=created.id,
        name="Stickbox Replacement",
        description=None,
        base_price_cents=3000,
        active=False,
    )

    assert updated.name == "Stickbox Replacement"
    assert updated.description is None
    assert updated.base_price_cents == 3000
    assert not updated.active
    assert len(list_catalog_items()) == 1


def test_event_catalog_prices_can_be_set_and_cleared(tmp_path: Path) -> None:
    event = _event(tmp_path)
    save_event(event)
    item = save_catalog_item(
        item_id=None,
        name="Paracord Cable",
        description=None,
        base_price_cents=2500,
        active=True,
    )
    assert item.id is not None

    save_event_catalog_price(event, item.id, 3000)
    assert event_catalog_prices(event) == {item.id: 3000}

    save_event_catalog_price(event, item.id, None)
    assert event_catalog_prices(event) == {}


def test_order_line_mapping_does_not_copy_persistence_identity() -> None:
    record = OrderLineRecord(
        id=41,
        order_id=23,
        line_number=1,
        description="Repair",
        quantity=1,
        unit_price_cents=2500,
    )

    mapped = _order_line_record(record)

    assert mapped.id is None
    assert mapped.order_id is None
    assert mapped.description == "Repair"


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
        line_items=[
            OrderLine(
                line_number=1,
                catalog_item_id=None,
                description="Custom repair",
                quantity=1,
                unit_price_cents=1250,
            )
        ],
    )

    append_order(order)

    assert orders_db_path(event).exists()
    assert next_order_id(event) == 2
    assert list_order_records(event)[0].phone == "+16502530000"
    export_path = event.path / "orders.csv"
    with export_path.open(encoding="utf-8-sig", newline="") as file:
        exported_rows = list(csv.DictReader(file))
    assert len(exported_rows) == 1
    assert exported_rows[0]["line_items"] == "1 x Custom repair @ 12.50"
    assert exported_rows[0]["timestamp"] == timestamp.isoformat(timespec="minutes")
    assert "catalog_item_id" not in exported_rows[0]

    saved = get_order(event, 1)
    assert saved is not None
    assert saved.work_request == "Original"
    assert len(saved.line_items) == 1
    assert saved.line_items[0].description == "Custom repair"

    update_order(
        saved.model_copy(
            update={
                "work_request": "Updated",
                "cost": "30.00",
                "label_filename": "new.png",
                "line_items": [
                    OrderLine(
                        line_number=1,
                        catalog_item_id=None,
                        description="Replacement service",
                        quantity=2,
                        unit_price_cents=1500,
                    )
                ],
            }
        )
    )

    orders = list_order_records(event)
    assert len(orders) == 1
    assert orders[0].work_request == "Updated"
    assert orders[0].label_filename == "new.png"
    updated = get_order(event, 1)
    assert updated is not None
    assert len(updated.line_items) == 1
    assert updated.line_items[0].description == "Replacement service"
    assert updated.line_items[0].quantity == 2
    with export_path.open(encoding="utf-8-sig", newline="") as file:
        exported_rows = list(csv.DictReader(file))
    assert len(exported_rows) == 1
    assert exported_rows[0]["line_items"] == "2 x Replacement service @ 15.00"
    assert exported_rows[0]["order_total"] == "30.00"
