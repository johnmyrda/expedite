"""Native startup must not leave an invisible window after a failed handshake probe."""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from nicegui import app

from expedite.main import _show_native_window_when_ready


@dataclass
class StubWindow:
    responses: list[str | Exception] = field(default_factory=list)
    probes: int = 0
    shown: bool = False
    title: str | None = None
    fail_show: bool = False

    async def evaluate_js(self, script: str) -> str:
        assert "did_handshake" in script
        self.probes += 1
        response = self.responses.pop(0) if self.responses else "waiting"
        if isinstance(response, Exception):
            raise response
        return response

    def set_title(self, title: str) -> None:
        self.title = title

    def show(self) -> None:
        if self.fail_show:
            raise RuntimeError("window could not be shown")
        self.shown = True


def test_native_window_retries_transient_error_before_marking_ready(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    window = StubWindow([RuntimeError("webview not ready"), "waiting", "ready"])
    monkeypatch.setattr(app.native, "main_window", window)
    marker = tmp_path / "smoke" / "ready"

    asyncio.run(_show_native_window_when_ready(marker, handshake_timeout=0.5))

    assert window.probes == 3
    assert window.shown
    assert window.title is None
    assert marker.read_text(encoding="utf-8") == "ready\n"


def test_native_window_shows_diagnostic_title_when_probes_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    window = StubWindow([RuntimeError("webview not ready")])
    monkeypatch.setattr(app.native, "main_window", window)
    marker = tmp_path / "ready"

    with caplog.at_level(logging.ERROR):
        asyncio.run(_show_native_window_when_ready(marker, handshake_timeout=0.08))

    assert window.probes >= 2
    assert window.shown
    assert window.title == "Expedite - Startup connection unavailable"
    assert not marker.exists()
    assert "Native startup did not reach the NiceGUI handshake" in caplog.text


def test_timed_out_probe_does_not_start_another_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    class HangingWindow(StubWindow):
        async def evaluate_js(self, script: str) -> str:
            self.probes += 1
            await asyncio.Event().wait()
            return "ready"

    window = HangingWindow()
    monkeypatch.setattr(app.native, "main_window", window)
    marker = tmp_path / "ready"

    with caplog.at_level(logging.ERROR):
        asyncio.run(
            _show_native_window_when_ready(marker, handshake_timeout=0.5, probe_timeout=0.02)
        )

    assert window.probes == 1
    assert window.shown
    assert window.title == "Expedite - Startup connection unavailable"
    assert not marker.exists()
    assert "Native handshake probe timed out" in caplog.text


def test_title_failure_does_not_prevent_revealing_window(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    class UntitledWindow(StubWindow):
        def set_title(self, title: str) -> None:
            raise RuntimeError("could not change title")

    window = UntitledWindow()
    monkeypatch.setattr(app.native, "main_window", window)
    marker = tmp_path / "ready"

    with caplog.at_level(logging.ERROR):
        asyncio.run(_show_native_window_when_ready(marker, handshake_timeout=0.01))

    assert window.shown
    assert not marker.exists()
    assert "Could not label the native window" in caplog.text


def test_smoke_marker_requires_successful_window_show(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    window = StubWindow(["ready"], fail_show=True)
    monkeypatch.setattr(app.native, "main_window", window)
    marker = tmp_path / "ready"

    with pytest.raises(RuntimeError, match="could not be shown"):
        asyncio.run(_show_native_window_when_ready(marker))

    assert not marker.exists()
