"""Helpers for opening local files and folders."""

import os
import subprocess
import sys
from pathlib import Path


def open_local_path(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
        return

    command = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([command, str(path)])
