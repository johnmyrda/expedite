"""Events landing page."""

from datetime import datetime

from nicegui import ui

from expedite.config import APP_NAME, data_dir
from expedite.local_files import open_local_path
from expedite.models import Event
from expedite.pages.components import (
    application_menu,
    application_status,
    classic_dialog,
    enable_list_keyboard,
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
            state: dict[str, str | None] = {"selected_folder": None}

            def selected_event() -> Event | None:
                return next(
                    (event for event in events if event.folder_name() == state["selected_folder"]),
                    None,
                )

            def navigate_selected(suffix: str = "") -> None:
                event = selected_event()
                if event is not None:
                    ui.navigate.to(f"/events/{event.folder_name()}{suffix}")

            @ui.refreshable
            def events_status() -> None:
                event = selected_event()
                detail = (
                    f"{event.name} selected · {len(events)} event(s)"
                    if event is not None
                    else f"{len(events)} event(s)"
                )
                application_status("Ready", detail)

            with group_box("Recent Events"):
                row_elements = {}

                def configure_toolbar() -> None:
                    enabled = selected_event() is not None
                    intake_button.enabled = enabled
                    orders_button.enabled = enabled
                    management_button.enabled = enabled

                def select_event(folder_name: str) -> None:
                    previous = state["selected_folder"]
                    if previous in row_elements:
                        row_elements[previous].classes(remove="is-selected")
                    state["selected_folder"] = folder_name
                    row_elements[folder_name].classes(add="is-selected")
                    configure_toolbar()
                    events_status.refresh()

                with ui.row().classes("classic-list-toolbar w-full items-center gap-1"):
                    intake_button = ui.button(
                        icon="assignment",
                        on_click=lambda: navigate_selected(),
                    ).props("flat round dense")
                    intake_button.props["aria-label"] = "Open Intake"
                    intake_button.tooltip("Open Intake")
                    orders_button = ui.button(
                        icon="receipt_long",
                        on_click=lambda: navigate_selected("/orders"),
                    ).props("flat round dense")
                    orders_button.props["aria-label"] = "Open Orders"
                    orders_button.tooltip("Open Orders")
                    management_button = ui.button(
                        icon="settings",
                        on_click=lambda: navigate_selected("/manage"),
                    ).props("flat round dense")
                    management_button.props["aria-label"] = "Open Management"
                    management_button.tooltip("Open Management")
                    configure_toolbar()

                with (
                    ui.element("div").classes("classic-list-panel"),
                    ui.element("table")
                    .classes("classic-list event-list")
                    .props('aria-label="Recent events"') as event_table,
                ):
                    enable_list_keyboard(event_table)
                    with ui.element("thead"), ui.element("tr"):
                        for heading, width in (
                            ("Event", "40%"),
                            ("Start Date", "180px"),
                            ("Folder", "auto"),
                        ):
                            with ui.element("th").style(f"width: {width}"):
                                ui.label(heading)
                    with ui.element("tbody"):
                        if not events:
                            with (
                                ui.element("tr"),
                                ui.element("td").props("colspan=3"),
                            ):
                                ui.label("No events yet. Choose New Event... to begin.")

                        for event in events:
                            folder_name = event.folder_name()
                            row = ui.element("tr").classes("classic-list-row")
                            row_elements[folder_name] = row
                            row.on(
                                "click",
                                lambda folder=folder_name: select_event(folder),
                            ).on(
                                "dblclick",
                                lambda folder=folder_name: ui.navigate.to(f"/events/{folder}"),
                            )
                            with row:
                                with ui.element("td"):
                                    ui.label(event.name).classes("font-medium")
                                with ui.element("td"):
                                    ui.label(event.start_date)
                                with ui.element("td"):
                                    ui.label(folder_name)

            events_status()
