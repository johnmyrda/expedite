"""Events landing page."""

from datetime import datetime

from nicegui import ui

from expedite.config import APP_NAME, data_dir
from expedite.local_files import open_local_path
from expedite.pages.components import (
    application_menu,
    application_status,
    classic_dialog,
    group_box,
    labeled_field,
)
from expedite.storage.events import create_event, list_events
from expedite.theme import apply_windows_98_theme


def register_events_page() -> None:
    @ui.page("/")
    def events_page() -> None:
        apply_windows_98_theme()
        ui.page_title(APP_NAME)

        with ui.column().classes("app-page w-full p-6 gap-6"):
            app_data_dir = data_dir()

            def create_new_event() -> None:
                name = (event_name_input.value or "").strip()
                if not name:
                    ui.notify("Event name is required.", type="negative")
                    event_name_input.run_method("focus")
                    return
                start_date = (event_date_input.value or "").strip()
                if not start_date:
                    ui.notify("Start date is required.", type="negative")
                    event_date_input.run_method("focus")
                    return
                event = create_event(name, start_date)
                ui.navigate.to(f"/events/{event.folder_name()}")

            with classic_dialog(
                "New Event",
                accept_label="Create",
                on_accept=create_new_event,
                width="460px",
            ) as new_event_dialog:
                with group_box("Event Details"):
                    with labeled_field("Event name"):
                        event_name_input = (
                            ui.input().props("outlined maxlength=120").classes("w-full")
                        )
                    with labeled_field("Start date"):
                        event_date_input = ui.input().props("outlined type=date").classes("w-full")
                new_event_dialog.set_initial_focus(event_name_input)

            def open_new_event() -> None:
                event_name_input.value = ""
                event_date_input.value = datetime.now().astimezone().date().isoformat()
                new_event_dialog.open()

            application_menu()
            with ui.row().classes("app-page-header w-full items-center justify-between"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(APP_NAME).classes("app-page-title text-3xl font-bold")
                    ui.button(
                        icon="folder_open",
                        on_click=lambda: open_local_path(app_data_dir),
                    ).props("flat round dense").classes("text-primary").tooltip(str(app_data_dir))
                ui.button("New Event...", on_click=open_new_event).props("color=primary")

            events = list_events()
            with group_box("Recent Events"):
                if not events:
                    ui.label("No events yet. Choose New Event... to begin.").classes(
                        "text-gray-500"
                    )
                else:
                    for event in events:
                        with ui.row().classes("w-full items-center justify-between border-b py-2"):
                            with ui.column().classes("gap-0"):
                                ui.link(
                                    event.name,
                                    f"/events/{event.folder_name()}/manage",
                                ).classes("font-medium text-primary no-underline")
                                ui.label(f"{event.start_date} · {event.folder_name()}").classes(
                                    "text-sm text-gray-500"
                                )
                            with ui.row().classes("gap-2"):
                                ui.button(
                                    "Intake",
                                    on_click=lambda e=event: ui.navigate.to(
                                        f"/events/{e.folder_name()}"
                                    ),
                                )
                                ui.button(
                                    "Orders",
                                    on_click=lambda e=event: ui.navigate.to(
                                        f"/events/{e.folder_name()}/orders"
                                    ),
                                ).props("flat")

            application_status("Ready", f"{len(events)} event(s)")
