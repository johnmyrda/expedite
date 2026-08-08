"""NiceGUI application entry point."""

from nicegui import ui

from expedite.config import APP_NAME
from expedite.pages.events import register_events_page
from expedite.pages.intake import register_intake_page
from expedite.pages.orders import register_orders_page
from expedite.storage.events import ensure_data_dir


def main() -> None:
    ensure_data_dir()
    register_events_page()
    register_intake_page()
    register_orders_page()
    ui.run(title=APP_NAME, native=True, reload=False, show=False)


if __name__ in {"__main__", "__mp_main__"}:
    main()
