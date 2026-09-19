from pathlib import Path

import pytest
from PIL import Image

from expedite import printing


class FakeWin32Print:
    PRINTER_ENUM_LOCAL = 1
    PRINTER_ENUM_CONNECTIONS = 2

    def __init__(
        self,
        printer_names: tuple[str, ...] = ("RONGTA 80mm Series Printer",),
    ) -> None:
        self.printer_names = printer_names
        self.calls: list[str] = []
        self.payload = b""
        self.handle = object()

    def EnumPrinters(self, flags: int) -> list[tuple[int, str, str, str]]:
        assert flags == 3
        return [(0, "", name, "") for name in self.printer_names]

    def OpenPrinter(self, printer_name: str) -> object:
        self.calls.append(f"open:{printer_name}")
        return self.handle

    def ClosePrinter(self, printer_handle: object) -> None:
        assert printer_handle is self.handle
        self.calls.append("close")

    def StartDocPrinter(
        self,
        printer_handle: object,
        level: int,
        document_info: tuple[str, None, str],
    ) -> int:
        assert printer_handle is self.handle
        assert level == 1
        assert document_info[2] == "RAW"
        self.calls.append("start_doc")
        return 1

    def EndDocPrinter(self, printer_handle: object) -> None:
        assert printer_handle is self.handle
        self.calls.append("end_doc")

    def StartPagePrinter(self, printer_handle: object) -> None:
        assert printer_handle is self.handle
        self.calls.append("start_page")

    def EndPagePrinter(self, printer_handle: object) -> None:
        assert printer_handle is self.handle
        self.calls.append("end_page")

    def WritePrinter(self, printer_handle: object, data: bytes) -> int:
        assert printer_handle is self.handle
        self.payload = data
        self.calls.append("write")
        return len(data)


def _label(path: Path) -> None:
    image = Image.new("1", (8, 1), "white")
    image.putpixel((0, 0), 0)
    image.save(path)


def test_escpos_payload_contains_raster_feed_and_cut(tmp_path: Path) -> None:
    path = tmp_path / "label.png"
    _label(path)

    payload = printing._escpos_payload(path)

    assert payload.startswith(b"\x1b@\x1ba\x00\x1dv0\x00\x01\x00\x01\x00\x80")
    assert payload.endswith(b"\n\n\n\x1dVB\x00")


def test_print_label_queues_raw_escpos_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "label.png"
    _label(path)
    fake = FakeWin32Print()
    monkeypatch.setattr(printing.sys, "platform", "win32")
    monkeypatch.setattr(printing, "_load_win32print", lambda: fake)

    printer_name = printing.print_label(path, "rongta 80MM series printer")

    assert printer_name == "RONGTA 80mm Series Printer"
    assert fake.calls == [
        "open:RONGTA 80mm Series Printer",
        "start_doc",
        "start_page",
        "write",
        "end_page",
        "end_doc",
        "close",
    ]
    assert fake.payload.startswith(b"\x1b@")


def test_print_label_reports_missing_configured_printer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "label.png"
    _label(path)
    fake = FakeWin32Print(("Office Printer",))
    monkeypatch.setattr(printing.sys, "platform", "win32")
    monkeypatch.setattr(printing, "_load_win32print", lambda: fake)

    with pytest.raises(
        printing.PrintError,
        match='Printer "RONGTA 80mm Series Printer" is not installed',
    ):
        printing.print_label(path)
