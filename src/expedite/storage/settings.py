"""Application-wide settings persisted in SQLite."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image

from expedite.config import (
    APP_NAME,
    DEFAULT_LABEL_NOTES_HEIGHT_MM,
    LABEL_DPI,
    MAX_LABEL_NOTES_HEIGHT_MM,
)
from expedite.models import AppAsset, AppSetting
from expedite.storage.database import open_session, transaction
from expedite.storage.repositories import AppAssetRepository, AppSettingRepository

LABEL_NOTES_HEIGHT_KEY = "label_notes_height_mm"
RECEIPT_NAME_KEY = "receipt_name"
RECEIPT_LOGO_KEY = "receipt_logo_png"
MAX_LOGO_BYTES = 5 * 1024 * 1024
MAX_RECEIPT_NAME_LENGTH = 60


@dataclass(frozen=True)
class ReceiptSettings:
    name: str
    notes_height_mm: int
    logo_png: bytes | None

    @property
    def notes_height_px(self) -> int:
        return round(self.notes_height_mm * LABEL_DPI / 25.4)


def _notes_height(setting: AppSetting | None) -> int:
    if setting is None:
        return DEFAULT_LABEL_NOTES_HEIGHT_MM
    try:
        value = round(float(setting.value))
    except (TypeError, ValueError):
        return DEFAULT_LABEL_NOTES_HEIGHT_MM
    if not 0 <= value <= MAX_LABEL_NOTES_HEIGHT_MM:
        return DEFAULT_LABEL_NOTES_HEIGHT_MM
    return value


def receipt_settings() -> ReceiptSettings:
    with open_session() as session:
        settings_repository = AppSettingRepository(session)
        assets_repository = AppAssetRepository(session)
        notes_setting = settings_repository.get(LABEL_NOTES_HEIGHT_KEY)
        name_setting = settings_repository.get(RECEIPT_NAME_KEY)
        logo_asset = assets_repository.get(RECEIPT_LOGO_KEY)
        name = name_setting.value.strip() if name_setting is not None else ""
        logo_png = logo_asset.content if logo_asset is not None else None
    return ReceiptSettings(
        name=name or APP_NAME.upper(),
        notes_height_mm=_notes_height(notes_setting),
        logo_png=logo_png,
    )


def label_notes_height_mm() -> int:
    return receipt_settings().notes_height_mm


def label_notes_height_px() -> int:
    return receipt_settings().notes_height_px


def validate_receipt_logo_png(data: bytes | None) -> None:
    if data is None:
        return
    if len(data) > MAX_LOGO_BYTES:
        raise ValueError("Logo must be 5 MB or smaller.")
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format != "PNG":
                raise ValueError("Logo must be a PNG file.")
            image.verify()
    except (OSError, SyntaxError) as error:
        raise ValueError("Logo must be a valid PNG file.") from error


def _validate_receipt_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise ValueError("Receipt name cannot be empty.")
    if len(name) > MAX_RECEIPT_NAME_LENGTH:
        raise ValueError(f"Receipt name cannot exceed {MAX_RECEIPT_NAME_LENGTH} characters.")
    return name


def _save_text_setting(repository: AppSettingRepository, key: str, value: str) -> None:
    setting = repository.get(key)
    if setting is None:
        setting = AppSetting(key=key, value=value)
    else:
        setting.value = value
    repository.save(setting)


def save_receipt_settings(*, name: str, notes_height_mm: int, logo_png: bytes | None) -> None:
    validated_name = _validate_receipt_name(name)
    if not isinstance(notes_height_mm, int) or isinstance(notes_height_mm, bool):
        raise TypeError("Notes height must be a whole number of millimeters.")
    if not 0 <= notes_height_mm <= MAX_LABEL_NOTES_HEIGHT_MM:
        raise ValueError(f"Notes height must be between 0 and {MAX_LABEL_NOTES_HEIGHT_MM:g} mm.")
    validate_receipt_logo_png(logo_png)

    with transaction() as session:
        settings_repository = AppSettingRepository(session)
        assets_repository = AppAssetRepository(session)
        _save_text_setting(settings_repository, RECEIPT_NAME_KEY, validated_name)
        _save_text_setting(
            settings_repository,
            LABEL_NOTES_HEIGHT_KEY,
            str(notes_height_mm),
        )
        logo_asset = assets_repository.get(RECEIPT_LOGO_KEY)
        if logo_png is None:
            if logo_asset is not None:
                assets_repository.delete(logo_asset)
        elif logo_asset is None:
            assets_repository.save(AppAsset(key=RECEIPT_LOGO_KEY, content=logo_png))
        else:
            logo_asset.content = logo_png
            assets_repository.save(logo_asset)


def save_label_notes_height_mm(value: int) -> None:
    current = receipt_settings()
    save_receipt_settings(name=current.name, notes_height_mm=value, logo_png=current.logo_png)
