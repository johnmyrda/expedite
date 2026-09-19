from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from expedite.config import DEFAULT_LABEL_NOTES_HEIGHT_MM, LABEL_DPI
from expedite.storage.settings import (
    label_notes_height_mm,
    label_notes_height_px,
    receipt_settings,
    save_label_notes_height_mm,
    save_receipt_settings,
)


def test_receipt_notes_height_defaults_and_persists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVENT_INTAKE_DATA_DIR", str(tmp_path))

    assert label_notes_height_mm() == DEFAULT_LABEL_NOTES_HEIGHT_MM == 60

    save_label_notes_height_mm(75)

    assert label_notes_height_mm() == 75
    assert label_notes_height_px() == round(75 * LABEL_DPI / 25.4)


def test_receipt_branding_persists_in_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVENT_INTAKE_DATA_DIR", str(tmp_path))
    buffer = BytesIO()
    Image.new("RGBA", (120, 60), "black").save(buffer, format="PNG")
    logo_png = buffer.getvalue()

    save_receipt_settings(name="My Repair Shop", notes_height_mm=80, logo_png=logo_png)

    settings = receipt_settings()
    assert settings.name == "My Repair Shop"
    assert settings.notes_height_mm == 80
    assert settings.logo_png == logo_png


def test_receipt_branding_rejects_invalid_logo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVENT_INTAKE_DATA_DIR", str(tmp_path))

    with pytest.raises(ValueError, match="valid PNG"):
        save_receipt_settings(name="Expedite", notes_height_mm=60, logo_png=b"not a png")


def test_receipt_notes_height_rejects_out_of_range_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVENT_INTAKE_DATA_DIR", str(tmp_path))

    with pytest.raises(ValueError, match="between 0 and 200 mm"):
        save_label_notes_height_mm(201)
