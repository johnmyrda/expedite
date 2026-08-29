"""NiceGUI application entry point."""

import argparse
import logging
import os
from pathlib import Path

from nicegui import app, ui

from expedite.config import APP_NAME
from expedite.diagnostics import configure_diagnostics, log_unhandled_exception
from expedite.pages.catalog import register_catalog_page
from expedite.pages.event_details import register_event_details_page
from expedite.pages.events import register_events_page
from expedite.pages.intake import register_intake_page
from expedite.pages.orders import register_orders_page
from expedite.storage.events import ensure_data_dir


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


def _run(*, port: int | None, smoke_test_marker: Path | None) -> None:
    if smoke_test_marker is not None:
        def mark_native_window_shown() -> None:
            smoke_test_marker.parent.mkdir(parents=True, exist_ok=True)
            smoke_test_marker.write_text("shown\n", encoding="utf-8")
            logging.info("Native window shown; wrote smoke-test marker %s", smoke_test_marker)

        app.native.on("shown", mark_native_window_shown)

    ensure_data_dir()
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
