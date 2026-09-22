"""Shared navigation controls for related event pages."""

from typing import Literal

from nicegui import events, ui
from nicegui.elements.tabs import Tab, TabPanel

EventTab = Literal["intake", "orders", "management"]


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
