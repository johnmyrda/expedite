"""NiceGUI application entry point."""

import argparse
import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Protocol, cast

from nicegui import app, ui

from expedite.config import APP_NAME
from expedite.diagnostics import configure_diagnostics, log_unhandled_exception
from expedite.pages.catalog import register_catalog_page
from expedite.pages.event_details import register_event_details_page
from expedite.pages.events import register_events_page
from expedite.pages.intake import register_intake_page
from expedite.pages.orders import register_orders_page
from expedite.storage.events import ensure_data_dir
from expedite.theme import register_theme_assets


class NativeWindow(Protocol):
    """Native-window operations needed during startup."""

    async def evaluate_js(self, script: str) -> str: ...

    def show(self) -> None: ...


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expedite desktop application")
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="show a diagnostic console and write a persistent startup log",
    )
    parser.add_argument("--port", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--smoke-test-marker", type=Path, help=argparse.SUPPRESS)
    args, _ = parser.parse_known_args()
    return args


async def _show_native_window_when_ready(smoke_test_marker: Path | None) -> None:
    """Reveal the native window after NiceGUI's client-server handshake completes."""
    main_window = app.native.main_window
    if main_window is None:
        return
    window = cast(NativeWindow, main_window)

    client_ready = False
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        readiness = await window.evaluate_js(
            "window.did_handshake ? 'ready' : 'waiting'"
        )
        if readiness == "ready":
            client_ready = True
            break
        await asyncio.sleep(0.02)
    if not client_ready:
        logging.warning("NiceGUI handshake did not complete before revealing the native window")

    window.show()
    if smoke_test_marker is not None and client_ready:
        smoke_test_marker.parent.mkdir(parents=True, exist_ok=True)
        smoke_test_marker.write_text("ready\n", encoding="utf-8")
        logging.info("Native window ready; wrote smoke-test marker %s", smoke_test_marker)


def _run(*, port: int | None, smoke_test_marker: Path | None) -> None:
    native_window_revealed = False

    async def reveal_native_window() -> None:
        nonlocal native_window_revealed
        if native_window_revealed:
            return
        native_window_revealed = True
        await _show_native_window_when_ready(smoke_test_marker)

    app.native.window_args["hidden"] = True
    app.native.on("loaded", reveal_native_window)

    ensure_data_dir()
    register_theme_assets()
    register_catalog_page()
    register_event_details_page()
    register_events_page()
    register_intake_page()
    register_orders_page()
    logging.info("Starting NiceGUI native application on port %s", port or "auto")
    ui.run(title=APP_NAME, native=True, reload=False, show=False, port=port)


def main() -> None:
    args = _parse_args()
    diagnostic = args.diagnostic or os.environ.get("EXPEDITE_DIAGNOSTIC") == "1"
    if diagnostic:
        configure_diagnostics()

    try:
        _run(port=args.port, smoke_test_marker=args.smoke_test_marker)
    except Exception:
        if diagnostic:
            log_unhandled_exception()
        raise


if __name__ in {"__main__", "__mp_main__"}:
    main()
