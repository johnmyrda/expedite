"""Events landing page."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from nicegui import ui

from expedite.config import APP_NAME, data_dir
from expedite.local_files import open_local_path
from expedite.models import Event
from expedite.pages.application_shell import (
    ApplicationStatus,
    application_menu,
    application_status,
)
from expedite.pages.classic_ui import (
    adjacent_list_value,
    classic_dialog,
    enable_list_keyboard,
    group_box,
    labeled_field,
    sortable_header,
    update_list_row_selection,
)
from expedite.storage.events import create_event, list_events

EventSortKey = Literal["name", "start_date", "folder"]


@dataclass
class EventsPageState:
    """Mutable selection and sorting state for the events list."""

    selected_folder: str | None = None
    sort_key: EventSortKey = "start_date"
    sort_descending: bool = True


def register_events_page() -> None:
    @ui.page("/")
    def events_page() -> None:
        ui.page_title(APP_NAME)
        status = ApplicationStatus()

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
                new_event_dialog.element.props('data-testid="new-event-dialog"')
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

            application_menu(status)
            with ui.row().classes("app-page-header w-full items-center justify-between"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(APP_NAME).classes("app-page-title text-3xl font-bold")
                    data_folder_button = ui.button(
                        icon="folder_open",
                        on_click=lambda: open_local_path(app_data_dir),
                    ).props("flat round dense").classes("text-primary")
                    data_folder_button.props["aria-label"] = "Open data folder"
                    data_folder_button.tooltip(str(app_data_dir))
                ui.button("New Event...", on_click=open_new_event).props(
                    'color=primary data-testid="new-event"'
                )

            events = list_events()
            state = EventsPageState()

            def sorted_events() -> list[Event]:
                key = state.sort_key
                key_functions = {
                    "name": lambda event: event.name.casefold(),
                    "start_date": lambda event: event.start_date,
                    "folder": lambda event: event.folder_name().casefold(),
                }
                return sorted(
                    events,
                    key=key_functions[key],
                    reverse=state.sort_descending,
                )

            def selected_event() -> Event | None:
                return next(
                    (event for event in events if event.folder_name() == state.selected_folder),
                    None,
                )

            def navigate_selected(suffix: str = "") -> None:
                event = selected_event()
                if event is not None:
                    ui.navigate.to(f"/events/{event.folder_name()}{suffix}")

            def update_status() -> None:
                event = selected_event()
                detail = (
                    f"{event.name} selected · {len(events)} event(s)"
                    if event is not None
                    else f"{len(events)} event(s)"
                )
                status.update("Ready", detail)

            with group_box("Recent Events"):
                row_elements = {}

                def configure_toolbar() -> None:
                    enabled = selected_event() is not None
                    intake_button.enabled = enabled
                    orders_button.enabled = enabled
                    management_button.enabled = enabled

                def select_event(folder_name: str) -> None:
                    update_list_row_selection(
                        event_table,
                        row_elements,
                        previous=state.selected_folder,
                        selected=folder_name,
                    )
                    state.selected_folder = folder_name
                    configure_toolbar()
                    update_status()

                def move_selection(offset: int) -> None:
                    folders = [event.folder_name() for event in sorted_events()]
                    folder_name = adjacent_list_value(folders, state.selected_folder, offset)
                    if folder_name is None:
                        return
                    select_event(folder_name)
                    row_elements[folder_name].run_method(
                        "scrollIntoView", {"block": "nearest"}
                    )

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
                    enable_list_keyboard(
                        event_table,
                        on_move=move_selection,
                        on_activate=lambda: navigate_selected(),
                    )

                    @ui.refreshable
                    def event_table_contents() -> None:
                        row_elements.clear()

                        def change_sort(key: EventSortKey) -> None:
                            if state.sort_key == key:
                                state.sort_descending = not state.sort_descending
                            else:
                                state.sort_key = key
                                state.sort_descending = False
                            event_table_contents.refresh()

                        with ui.element("thead"), ui.element("tr"):
                            for heading, key, width in (
                                ("Event", "name", "40%"),
                                ("Start Date", "start_date", "180px"),
                                ("Folder", "folder", "auto"),
                            ):
                                with ui.element("th").style(f"width: {width}"):
                                    sortable_header(
                                        heading,
                                        active=state.sort_key == key,
                                        descending=state.sort_descending,
                                        on_click=lambda sort_key=key: change_sort(sort_key),
                                    )
                        with ui.element("tbody"):
                            if not events:
                                with (
                                    ui.element("tr"),
                                    ui.element("td").props("colspan=3"),
                                ):
                                    ui.label("No events yet. Choose New Event... to begin.")

                            for event in sorted_events():
                                folder_name = event.folder_name()
                                selected = folder_name == state.selected_folder
                                row = ui.element("tr").classes(
                                    "classic-list-row" + (" is-selected" if selected else "")
                                )
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

                    event_table_contents()

            update_status()
            application_status(status)
