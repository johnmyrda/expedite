"""Shared navigation controls for related event pages."""

from typing import Literal

from nicegui import events, ui
from nicegui.elements.label import Label
from nicegui.elements.tabs import Tab, TabPanel

from expedite.local_files import open_local_path
from expedite.models import Event
from expedite.pages.application_shell import (
    ApplicationStatus,
    application_menu,
    application_status,
)

EventTab = Literal["intake", "orders", "management"]


def event_not_found_page() -> None:
    """Render the shared missing-event page content."""
    status = ApplicationStatus("Event not found")
    with ui.column().classes("app-page w-full p-6 gap-4"):
        application_menu(status)
        ui.label("Event not found").classes("text-2xl font-bold text-negative")
        ui.button("Back to Events", on_click=lambda: ui.navigate.to("/"))
        application_status(status)


def event_page_header(event: Event) -> Label:
    """Render the consistent header shared by all event routes."""
    with (
        ui.row().classes("app-page-header w-full items-center justify-between"),
        ui.row().classes("event-header-main min-w-0 items-center gap-2"),
    ):
        title = ui.label(event.name).classes("app-page-title text-3xl font-bold")
        folder_button = ui.button(
            icon="folder_open",
            on_click=lambda: open_local_path(event.path),
        ).props("flat round dense").classes("text-primary")
        folder_button.props["aria-label"] = f"Open folder for {event.name}"
        folder_button.tooltip(str(event.path))
    return title


def event_navigation_tabs(folder_name: str, active: EventTab) -> None:
    """Render route-backed tabs for the related event workflows."""
    routes = {
        "intake": f"/events/{folder_name}",
        "orders": f"/events/{folder_name}/orders",
        "management": f"/events/{folder_name}/manage",
    }

    with (
        ui.tabs()
        .props("dense no-caps align=left indicator-color=transparent")
        .classes("event-tabs w-full") as tabs
    ):
        tab_by_name: dict[EventTab, Tab] = {
            "intake": ui.tab("intake", label="Intake"),
            "orders": ui.tab("orders", label="Orders"),
            "management": ui.tab("management", label="Management"),
        }
    tabs.value = tab_by_name[active]

    def navigate(
        change: events.ValueChangeEventArguments[str | Tab | TabPanel | None],
    ) -> None:
        value = change.value
        tab_name = value.props["name"] if isinstance(value, (Tab, TabPanel)) else value
        if tab_name == active:
            return
        route = routes.get(str(tab_name or ""))
        if route is not None:
            ui.navigate.to(route)

    tabs.on_value_change(navigate)
