"""Runtime diagnostics for packaged desktop builds."""

from __future__ import annotations

import logging
import os
import platform
import sys
from contextlib import suppress
from pathlib import Path
from typing import TextIO

_LOG_STREAMS: list[TextIO] = []


class _Tee:
    """Write text to each available diagnostic stream."""

    def __init__(self, *streams: TextIO) -> None:
        self.streams = streams

    def write(self, text: str) -> int:
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()

    def isatty(self) -> bool:
        return any(stream.isatty() for stream in self.streams)


def _diagnostic_log_path() -> Path:
    configured = os.environ.get("EXPEDITE_DIAGNOSTIC_LOG_DIR")
    if configured:
        return Path(configured) / "expedite-diagnostic.log"
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path.home() / ".local" / "state"
    return root / "Expedite" / "logs" / "expedite-diagnostic.log"


def _attach_windows_console() -> None:
    if sys.platform != "win32":
        return

    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    attached = kernel32.AttachConsole(0xFFFFFFFF) != 0  # ATTACH_PARENT_PROCESS
    if not attached and ctypes.get_last_error() != 5:  # ERROR_ACCESS_DENIED means already attached
        kernel32.AllocConsole()

    for name, target, mode in (
        ("stdin", "CONIN$", "r"),
        ("stdout", "CONOUT$", "w"),
        ("stderr", "CONOUT$", "w"),
    ):
        try:
            stream = open(target, mode, encoding="utf-8", buffering=1)  # noqa: SIM115
        except OSError:
            continue
        _LOG_STREAMS.append(stream)
        setattr(sys, name, stream)


def configure_diagnostics() -> Path:
    """Enable console and file diagnostics, returning the persistent log path."""
    os.environ["EXPEDITE_DIAGNOSTIC"] = "1"  # inherited by NiceGUI's native window process
    _attach_windows_console()

    log_path = _diagnostic_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    is_child = "--multiprocessing-fork" in sys.argv
    log_file = log_path.open("a" if is_child else "w", encoding="utf-8", buffering=1)
    _LOG_STREAMS.append(log_file)

    stdout_streams = tuple(stream for stream in (sys.stdout, log_file) if stream is not None)
    stderr_streams = tuple(stream for stream in (sys.stderr, log_file) if stream is not None)
    sys.stdout = _Tee(*stdout_streams)  # type: ignore[assignment]
    sys.stderr = _Tee(*stderr_streams)  # type: ignore[assignment]

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(process)d %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
        force=True,
    )
    logging.captureWarnings(True)
    logging.info("Expedite diagnostic mode enabled")
    logging.info("Log file: %s", log_path)
    logging.info("Platform: %s", platform.platform())
    logging.info("Python: %s", sys.version.replace("\n", " "))
    logging.info("Executable: %s", sys.executable)
    logging.info("Frozen: %s", bool(getattr(sys, "frozen", False)))
    logging.info("Arguments: %s", sys.argv)
    return log_path


def log_unhandled_exception() -> None:
    """Log the active exception and keep a diagnostic console visible when possible."""
    logging.exception("Expedite terminated because of an unhandled exception")
    if sys.platform == "win32" and "--multiprocessing-fork" not in sys.argv:
        with suppress(EOFError, OSError):
            input("Expedite failed. Press Enter to close this diagnostic window...")
