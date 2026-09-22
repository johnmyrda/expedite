#!/usr/bin/env python3
"""Run Expedite as a browser-only server for temporary UI iteration."""

import argparse
import os
import tempfile
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
    args = parser.parse_args()
    os.environ["EVENT_INTAKE_DATA_DIR"] = str(args.data_dir.resolve())

    from nicegui import ui

    from expedite.pages.catalog import register_catalog_page
    from expedite.pages.event_details import register_event_details_page
    from expedite.pages.events import register_events_page
    from expedite.pages.intake import register_intake_page
    from expedite.pages.orders import register_orders_page
    from expedite.storage.events import ensure_data_dir
    from expedite.theme import register_theme_assets

    ensure_data_dir()
    register_theme_assets()
    for register_page in (
        register_catalog_page,
        register_event_details_page,
        register_events_page,
        register_intake_page,
        register_orders_page,
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
