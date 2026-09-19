"""Application configuration for Expedite."""

import os
import sys
from pathlib import Path

APP_NAME = "Expedite"

FIELDS = ("Name", "Phone", "Work Request", "Cost")

# Rongta RP332 80mm thermal receipt printer target.
# Manufacturer specs: 203 DPI / 8 dots per mm, effective print width
# 72mm or 64mm, 576 or 384 dots per line. Use the wider 72mm mode for
# generated receipt-label images. Windows printing converts these PNGs to
# ESC/POS raster commands for direct spooler dispatch.
PRINTER_MODEL = "Rongta RP332"
PRINTER_NAME = os.environ.get("EXPEDITE_PRINTER_NAME", "RONGTA 80mm Series Printer")
LABEL_DPI = 203
LABEL_PRINTABLE_WIDTH_MM = 72
LABEL_WIDTH_PX = 576
MAX_LABEL_NOTES_HEIGHT_MM = 200.0
DEFAULT_LABEL_NOTES_HEIGHT_MM = min(
    MAX_LABEL_NOTES_HEIGHT_MM,
    max(0.0, float(os.environ.get("EXPEDITE_LABEL_NOTES_HEIGHT_MM", "60"))),
)


def _documents_dir() -> Path | None:
    if sys.platform == "win32":
        home = os.environ.get("USERPROFILE")
        if home:
            candidate = Path(home) / "Documents"
            if candidate.is_dir():
                return candidate

    candidate = Path.home() / "Documents"
    if candidate.is_dir():
        return candidate
    return None


def data_dir() -> Path:
    """Return the directory that stores event data.

    Can be overridden with EVENT_INTAKE_DATA_DIR. Otherwise defaults to an
    Expedite folder under the user's Documents directory when that directory
    is available, falling back to the repository's dev-time
    ``data/`` folder.
    """

    configured = os.environ.get("EVENT_INTAKE_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()

    documents = _documents_dir()
    if documents is not None:
        return documents / APP_NAME

    return Path.cwd() / "data"
