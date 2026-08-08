"""Application configuration for Expedite."""

import os
import sys
from pathlib import Path

APP_NAME = "Expedite"

FIELDS = ("Name", "Phone", "Work Request", "Cost")

# 4x6 inch label at common 203 DPI thermal-printer resolution.
LABEL_WIDTH_INCHES = 4
LABEL_HEIGHT_INCHES = 6
LABEL_DPI = 203
LABEL_SIZE_PX = (LABEL_WIDTH_INCHES * LABEL_DPI, LABEL_HEIGHT_INCHES * LABEL_DPI)


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
