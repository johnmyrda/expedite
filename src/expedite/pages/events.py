"""Events landing page."""

from datetime import datetime

from nicegui import ui

from expedite.config import APP_NAME, data_dir
from expedite.local_files import open_local_path
from expedite.storage.events import create_event, list_events


def register_events_page() -> None:
    @ui.page("/")
    def events_page() -> None:
        ui.page_title(APP_NAME)
        ui.add_head_html("<style>body { background: #f7f7f7; }</style>")

        with ui.column().classes("w-full max-w-3xl mx-auto p-6 gap-6"):
            app_data_dir = data_dir()
            with ui.row().classes("items-center gap-2"):
                ui.label(APP_NAME).classes("text-3xl font-bold")
                ui.button(
                    icon="folder_open",
                    on_click=lambda: open_local_path(app_data_dir),
                ).props("flat round dense").classes("text-primary").tooltip(
                    str(app_data_dir)
                )

            with ui.card().classes("w-full"):
                ui.label("Create New Event").classes("text-xl font-semibold")
                name_input = ui.input("Event name").props("outlined").classes("w-full")
                today = datetime.now().astimezone().date().isoformat()
                date_input = (
                    ui.input("Start date", value=today)
                    .props("outlined type=date")
                    .classes("w-full")
                )

                def handle_create() -> None:
                    event = create_event(
                        name_input.value or "Untitled Event", date_input.value or None
                    )
                    ui.navigate.to(f"/events/{event.folder_name()}")

                ui.button("Create New", on_click=handle_create).props("color=primary")

            with ui.card().classes("w-full"):
                ui.label("Recent Events").classes("text-xl font-semibold")
                events = list_events()
                if not events:
                    ui.label("No events yet. Create one above to begin.").classes(
                        "text-gray-500"
                    )
                else:
                    for event in events:
                        with ui.row().classes(
                            "w-full items-center justify-between border-b py-2"
                        ):
                            with ui.column().classes("gap-0"):
                                ui.label(event.name).classes("font-medium")
                                ui.label(
                                    f"{event.start_date} · {event.folder_name()}"
                                ).classes("text-sm text-gray-500")
                            with ui.row().classes("gap-2"):
                                ui.button(
                                    "Open",
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
