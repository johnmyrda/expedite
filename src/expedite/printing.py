"""Windows ESC/POS printing for generated receipt labels."""

from __future__ import annotations

import sys
from contextlib import suppress
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Protocol, cast

from PIL import Image, ImageOps

from expedite.config import PRINTER_NAME


class PrintError(RuntimeError):
    """Raised when a label cannot be queued for printing."""


class _Win32Print(Protocol):
    PRINTER_ENUM_LOCAL: int
    PRINTER_ENUM_CONNECTIONS: int

    def EnumPrinters(self, flags: int) -> list[tuple[int, str, str, str]]: ...

    def OpenPrinter(self, printer_name: str) -> object: ...

    def ClosePrinter(self, printer_handle: object) -> None: ...

    def StartDocPrinter(
        self,
        printer_handle: object,
        level: int,
        document_info: tuple[str, None, str],
    ) -> int: ...

    def EndDocPrinter(self, printer_handle: object) -> None: ...

    def StartPagePrinter(self, printer_handle: object) -> None: ...

    def EndPagePrinter(self, printer_handle: object) -> None: ...

    def WritePrinter(self, printer_handle: object, data: bytes) -> int: ...


def _load_win32print() -> _Win32Print:
    module: ModuleType = import_module("win32print")
    return cast(_Win32Print, module)


def _escpos_payload(label_path: Path) -> bytes:
    """Convert a label image to an ESC/POS raster command with feed and cut."""
    with Image.open(label_path) as source:
        grayscale = source.convert("L")

    width_bytes = (grayscale.width + 7) // 8
    padded_width = width_bytes * 8
    padded = Image.new("L", (padded_width, grayscale.height), "white")
    padded.paste(grayscale, (0, 0))
    raster = ImageOps.invert(padded).convert("1", dither=Image.Dither.NONE).tobytes()

    height = grayscale.height
    dimensions = bytes(
        (
            width_bytes & 0xFF,
            (width_bytes >> 8) & 0xFF,
            height & 0xFF,
            (height >> 8) & 0xFF,
        )
    )
    initialize = b"\x1b@"
    align_left = b"\x1ba\x00"
    raster_header = b"\x1dv0\x00" + dimensions
    feed_and_partial_cut = b"\n\n\n\x1dVB\x00"
    return initialize + align_left + raster_header + raster + feed_and_partial_cut


def _resolve_printer(win32print: _Win32Print, configured_name: str) -> str:
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    installed_names = [printer[2] for printer in win32print.EnumPrinters(flags)]
    match = next(
        (name for name in installed_names if name.casefold() == configured_name.casefold()),
        None,
    )
    if match is None:
        available = ", ".join(sorted(installed_names)) or "none"
        raise PrintError(
            f'Printer "{configured_name}" is not installed. Available printers: {available}.'
        )
    return match


def print_label(label_path: Path, printer_name: str = PRINTER_NAME) -> str:
    """Queue a generated label on the configured Windows ESC/POS printer."""
    if sys.platform != "win32":
        raise PrintError("Automatic label printing is currently supported only on Windows.")
    if not label_path.is_file():
        raise PrintError(f"Label image does not exist: {label_path}")

    win32print = _load_win32print()
    resolved_name = _resolve_printer(win32print, printer_name)
    payload = _escpos_payload(label_path)

    printer_handle: object | None = None
    document_started = False
    page_started = False
    try:
        printer_handle = win32print.OpenPrinter(resolved_name)
        win32print.StartDocPrinter(
            printer_handle,
            1,
            (f"Expedite - {label_path.stem}", None, "RAW"),
        )
        document_started = True
        win32print.StartPagePrinter(printer_handle)
        page_started = True
        written = win32print.WritePrinter(printer_handle, payload)
        if written != len(payload):
            raise PrintError(f"Printer accepted {written} of {len(payload)} bytes.")
        win32print.EndPagePrinter(printer_handle)
        page_started = False
        win32print.EndDocPrinter(printer_handle)
        document_started = False
    except PrintError:
        raise
    except Exception as error:
        raise PrintError(f'Could not print on "{resolved_name}": {error}') from error
    finally:
        if printer_handle is not None:
            if page_started:
                with suppress(Exception):
                    win32print.EndPagePrinter(printer_handle)
            if document_started:
                with suppress(Exception):
                    win32print.EndDocPrinter(printer_handle)
            with suppress(Exception):
                win32print.ClosePrinter(printer_handle)

    return resolved_name
