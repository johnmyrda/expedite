"""Application-wide menu and status-bar components."""

import json
from collections.abc import Callable

from nicegui import app, ui

from expedite.config import APP_NAME, data_dir
from expedite.local_files import open_local_path
from expedite.pages.classic_ui import classic_dialog
from expedite.pages.receipt_settings import receipt_settings_dialog


def exit_application() -> None:
    """Close the native window and stop the application server."""
    app.shutdown()


def application_menu(*, on_export: Callable[[], None] | None = None) -> None:
    """Render the application-wide menu bar."""
    open_receipt_settings = receipt_settings_dialog(on_saved=update_application_status)
    with classic_dialog(
        f"About {APP_NAME}",
        accept_label="OK",
        cancel_label=None,
        width="380px",
    ) as about_dialog:
        ui.label(APP_NAME).classes("classic-about-name")
        ui.label("Event order and receipt management").classes("text-sm")

    with ui.row().classes("app-menu-bar w-full items-center gap-0"):
        with ui.dropdown_button("File", auto_close=True, color=None).props(
            "flat dense no-caps dropdown-icon=none"
        ):
            ui.item("Events", on_click=lambda: ui.navigate.to("/"))
            if on_export is not None:
                ui.item("Export Orders...", on_click=on_export)
            ui.item("Open Data Folder", on_click=lambda: open_local_path(data_dir()))
            ui.separator()
            ui.item("Exit", on_click=exit_application).classes("exit-command")
        with ui.dropdown_button("Tools", auto_close=True, color=None).props(
            "flat dense no-caps dropdown-icon=none"
        ):
            ui.item("Catalog", on_click=lambda: ui.navigate.to("/catalog"))
            ui.item("Receipt Settings...", on_click=open_receipt_settings)
        with ui.dropdown_button("Help", auto_close=True, color=None).props(
            "flat dense no-caps dropdown-icon=none"
        ):
            ui.item(f"About {APP_NAME}", on_click=about_dialog.open).classes("about-command")


def update_application_status(message: str, detail: str | None = None) -> None:
    """Update the visible status bar without rebuilding the surrounding page."""
    message_json = json.dumps(message)
    detail_script = (
        ""
        if detail is None
        else (
            "const detail = document.querySelector('.app-status-detail');"
            f" if (detail) detail.textContent = {json.dumps(detail)};"
        )
    )
    ui.run_javascript(
        "const message = document.querySelector('.app-status-message');"
        f" if (message) message.textContent = {message_json};"
        f" {detail_script}"
    )


def application_status(message: str = "Ready", detail: str = "") -> None:
    """Render the application-wide status bar."""
    with ui.row().classes("app-status-bar w-full gap-1"):
        ui.label(message).classes("status-bar-field app-status-message grow")
        ui.label(detail).classes("status-bar-field app-status-detail")
