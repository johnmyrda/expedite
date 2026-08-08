"""Application configuration for Event Intake."""

import os
from pathlib import Path

APP_NAME = "Event Order Intake"

FIELDS = ("Name", "Phone", "Work Request", "Cost")

# 4x6 inch label at common 203 DPI thermal-printer resolution.
LABEL_WIDTH_INCHES = 4
LABEL_HEIGHT_INCHES = 6
LABEL_DPI = 203
LABEL_SIZE_PX = (LABEL_WIDTH_INCHES * LABEL_DPI, LABEL_HEIGHT_INCHES * LABEL_DPI)


def data_dir() -> Path:
    """Return the directory that stores event data.

    Defaults to the repository's dev-time ``data/`` folder. Can be overridden
    with EVENT_INTAKE_DATA_DIR for deployments or manual testing.
    """

    configured = os.environ.get("EVENT_INTAKE_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.cwd() / "data"
