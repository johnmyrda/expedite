"""Reusable classic desktop UI components."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from nicegui import ui

from expedite.config import APP_NAME, data_dir
from expedite.local_files import open_local_path


@contextmanager
def group_box(title: str) -> Iterator[None]:
    """Render a classic labeled group box."""
    with ui.element("fieldset").classes("classic-group w-full"):
        with ui.element("legend").classes("classic-group-legend"):
            ui.label(title)
        yield


@contextmanager
def labeled_field(label: str, *, classes: str = "w-full") -> Iterator[None]:
    """Render an explicit label above a form control."""
    with ui.column().classes(f"classic-field gap-1 {classes}"):
        ui.label(label).classes("classic-field-label")
        yield


def application_menu(*, on_export: Callable[[], None] | None = None) -> None:
    """Render the application-wide menu bar."""
    with ui.row().classes("app-menu-bar w-full items-center gap-0"):
        with ui.dropdown_button("File", auto_close=True, color=None).props(
            "flat dense no-caps dropdown-icon=none"
        ):
            ui.item("Events", on_click=lambda: ui.navigate.to("/"))
            if on_export is not None:
                ui.item("Export Orders...", on_click=on_export)
            ui.item("Open Data Folder", on_click=lambda: open_local_path(data_dir()))
        with ui.dropdown_button("Tools", auto_close=True, color=None).props(
            "flat dense no-caps dropdown-icon=none"
        ):
            ui.item("Catalog", on_click=lambda: ui.navigate.to("/catalog"))
        with ui.dropdown_button("Help", auto_close=True, color=None).props(
            "flat dense no-caps dropdown-icon=none"
        ):
            ui.item(
                f"About {APP_NAME}",
                on_click=lambda: ui.notify(f"{APP_NAME} event order management", type="info"),
            )


def application_status(message: str = "Ready", detail: str = "") -> None:
    """Render the application-wide status bar."""
    with ui.row().classes("app-status-bar w-full gap-1"):
        ui.label(message).classes("status-bar-field grow")
        if detail:
            ui.label(detail).classes("status-bar-field")
