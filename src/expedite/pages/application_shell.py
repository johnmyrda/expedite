"""Application-wide menu and status-bar components."""

from collections.abc import Callable

from nicegui import app, binding, ui

from expedite.config import APP_NAME, data_dir
from expedite.local_files import open_local_path
from expedite.pages.classic_ui import classic_dialog
from expedite.pages.receipt_settings import receipt_settings_dialog


@binding.bindable_dataclass
class ApplicationStatus:
    """Page-scoped state displayed in the application status bar."""

    message: str = "Ready"
    detail: str = ""

    def update(self, message: str, detail: str | None = None) -> None:
        """Update the status while retaining the current detail when omitted."""
        self.message = message
        if detail is not None:
            self.detail = detail


def exit_application() -> None:
    """Close the native window and stop the application server."""
    app.shutdown()


def application_menu(
    status: ApplicationStatus,
    *,
    on_export: Callable[[], None] | None = None,
) -> None:
    """Render the application-wide menu bar."""
    open_receipt_settings = receipt_settings_dialog(on_saved=status.update)
    with classic_dialog(
        f"About {APP_NAME}",
        accept_label="OK",
        cancel_label=None,
        width="380px",
        footer_text="© 2026 John Myrda",
    ) as about_dialog:
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


def application_status(status: ApplicationStatus) -> None:
    """Render a status bar bound to page-scoped state."""
    # Layout elements must be direct children of the page, even when called from a page column.
    with (
        ui.context.client.content,
        ui.footer(fixed=True).classes("app-status-bar"),
        ui.row().classes("w-full gap-1"),
    ):
        ui.label().classes("status-bar-field app-status-message grow").bind_text_from(
            status, "message"
        )
        ui.label().classes("status-bar-field app-status-detail").bind_text_from(
            status, "detail"
        )
