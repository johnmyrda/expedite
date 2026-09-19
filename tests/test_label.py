from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image

from expedite import label
from expedite.models import Event, Order


def _order(tmp_path: Path, *, cost: str = "0.00") -> Order:
    event = Event(
        name="Test Event",
        start_date="2026-08-08",
        created_at=datetime(2026, 8, 1).astimezone(),
        path=tmp_path / "test_event",
    )
    return Order.model_construct(
        order_id=1,
        timestamp=datetime(2026, 8, 8, 12, 30).astimezone(),
        name="Jane Customer",
        phone="+16502530000",
        work_request="Controller repair",
        cost=cost,
        event=event,
        line_items=[],
    )


def test_receipt_cost_is_blank_only_for_zero() -> None:
    assert label._receipt_cost("0.00") == ""
    assert label._receipt_cost("$0") == ""
    assert label._receipt_cost("12.50") == "12.50"


def test_notes_area_adds_configured_height(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = _order(tmp_path)
    monkeypatch.setattr(label, "LABEL_NOTES_HEIGHT_PX", 240)
    receipt_path = label.render_label(order)
    with Image.open(receipt_path) as receipt:
        height_with_notes = receipt.height

    monkeypatch.setattr(label, "LABEL_NOTES_HEIGHT_PX", 0)
    receipt_path = label.render_label(order)
    with Image.open(receipt_path) as receipt:
        height_without_notes = receipt.height

    assert height_with_notes - height_without_notes == 240
