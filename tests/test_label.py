from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from expedite import label
from expedite.models import Event, Order
from expedite.storage.settings import ReceiptSettings


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
    monkeypatch.setattr(
        label,
        "receipt_settings",
        lambda: ReceiptSettings(name="EXPEDITE", notes_height_mm=30.0, logo_png=None),
    )
    receipt_path = label.render_label(order)
    with Image.open(receipt_path) as receipt:
        height_with_notes = receipt.height

    monkeypatch.setattr(
        label,
        "receipt_settings",
        lambda: ReceiptSettings(name="EXPEDITE", notes_height_mm=0.0, logo_png=None),
    )
    receipt_path = label.render_label(order)
    with Image.open(receipt_path) as receipt:
        height_without_notes = receipt.height

    assert height_with_notes - height_without_notes == round(30 * 203 / 25.4)


def test_receipt_logo_preserves_aspect_ratio_and_transparency() -> None:
    source = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
    source.paste((0, 0, 0, 255), (100, 50, 300, 150))
    buffer = BytesIO()
    source.save(buffer, format="PNG")

    logo = label._receipt_logo(buffer.getvalue(), max_width=200, max_height=180)

    assert logo is not None
    assert logo.size == (200, 100)
    assert logo.mode == "RGB"
    assert logo.getpixel((0, 0)) == (255, 255, 255)
