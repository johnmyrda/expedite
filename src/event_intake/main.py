"""NiceGUI application entry point."""

from nicegui import ui

from event_intake.config import APP_NAME
from event_intake.pages.events import register_events_page
from event_intake.pages.intake import register_intake_page
from event_intake.storage.events import ensure_data_dir


def main() -> None:
    ensure_data_dir()
    register_events_page()
    register_intake_page()
    ui.run(title=APP_NAME, native=True, reload=False, show=False)


if __name__ in {"__main__", "__mp_main__"}:
    main()
