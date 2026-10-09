#!/usr/bin/env python3
"""Run Expedite as a browser-only server for temporary UI iteration."""

import argparse
import os
import tempfile
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(
            os.environ.get(
                "EVENT_INTAKE_DATA_DIR",
                Path(tempfile.gettempdir()) / "expedite-ui-preview",
            )
        ),
    )
    parser.add_argument(
        "--fake-print-delay",
        type=float,
        help="Use a fake printer which completes after the given number of seconds.",
    )
    args = parser.parse_args()
    os.environ["EVENT_INTAKE_DATA_DIR"] = str(args.data_dir.resolve())

    from nicegui import ui

    from expedite.pages import intake, orders
    from expedite.pages.catalog import register_catalog_page
    from expedite.pages.event_details import register_event_details_page
    from expedite.pages.events import register_events_page
    from expedite.storage.events import ensure_data_dir
    from expedite.theme import register_theme_assets

    fake_print = None
    if args.fake_print_delay is not None:
        if args.fake_print_delay < 0:
            parser.error("--fake-print-delay must not be negative")

        def fake_print(_path: Path) -> str:
            time.sleep(args.fake_print_delay)
            return "UI test printer"

    ensure_data_dir()
    register_theme_assets()
    for register_page in (
        register_catalog_page,
        register_event_details_page,
        register_events_page,
        lambda: intake.register_intake_page(print_label_fn=fake_print or intake.print_label),
        lambda: orders.register_orders_page(print_label_fn=fake_print or orders.print_label),
    ):
        register_page()

    ui.run(
        title="Expedite UI Preview",
        native=False,
        reload=False,
        show=False,
        host="127.0.0.1",
        port=args.port,
    )


if __name__ == "__main__":
    main()
