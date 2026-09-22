"""Reusable classic desktop UI components."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from nicegui import ui
from nicegui.element import Element
from nicegui.elements.button import Button
from nicegui.elements.dialog import Dialog

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


@dataclass
class ClassicDialog:
    """Controller for a reusable classic modal dialog."""

    element: Dialog
    default_button: Button | None = None
    initial_focus: Element | None = None

    def set_initial_focus(self, element: Element) -> None:
        """Set the control which receives focus when the dialog opens."""
        self.initial_focus = element

    def open(self) -> None:
        """Open the dialog and move focus to its initial control."""
        self.element.open()
        target = self.initial_focus or self.default_button
        if target is not None:
            ui.timer(
                0.1,
                lambda: ui.run_javascript(
                    f"""
                    const root = document.getElementById('{target.html_id}');
                    const control = root?.matches('input, select, textarea, button')
                        ? root
                        : root?.querySelector('input, select, textarea, button');
                    control?.focus();
                    """
                ),
                once=True,
            )

    def close(self) -> None:
        """Close the dialog."""
        self.element.close()


@contextmanager
def classic_dialog(
    title: str,
    *,
    accept_label: str = "OK",
    cancel_label: str | None = "Cancel",
    apply_label: str = "Apply",
    on_accept: Callable[[], object] | None = None,
    on_apply: Callable[[], object] | None = None,
    width: str = "520px",
) -> Iterator[ClassicDialog]:
    """Render a classic modal with standard action placement and keyboard behavior."""
    dialog = ui.dialog()
    controller = ClassicDialog(dialog)

    def accept() -> object | None:
        if on_accept is None:
            dialog.close()
            return None
        return on_accept()

    with (
        dialog,
        ui.card()
        .classes("classic-dialog")
        .style(f"width: min({width}, calc(100vw - 32px))") as card,
    ):
        ui.label(title).classes("classic-dialog-title")
        ui.separator()
        with ui.column().classes("classic-dialog-body w-full"):
            yield controller
        ui.separator()
        with ui.row().classes("classic-dialog-actions w-full justify-end gap-2"):
            controller.default_button = (
                ui.button(accept_label, on_click=accept)
                .props("color=primary")
                .classes("classic-default-button")
            )
            if cancel_label is not None:
                ui.button(cancel_label, on_click=dialog.close).props("flat")
            if on_apply is not None:
                ui.button(apply_label, on_click=on_apply).props("flat")

        card.on(
            "keydown",
            js_handler=(
                "(event) => {"
                " if (event.key === 'Enter'"
                " && event.target.tagName !== 'TEXTAREA'"
                " && event.target.tagName !== 'BUTTON') {"
                " event.preventDefault();"
                f" document.getElementById('{controller.default_button.html_id}')?.click();"
                " }"
                "}"
            ),
        )


def application_menu(*, on_export: Callable[[], None] | None = None) -> None:
    """Render the application-wide menu bar."""
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
        with ui.dropdown_button("Tools", auto_close=True, color=None).props(
            "flat dense no-caps dropdown-icon=none"
        ):
            ui.item("Catalog", on_click=lambda: ui.navigate.to("/catalog"))
        with ui.dropdown_button("Help", auto_close=True, color=None).props(
            "flat dense no-caps dropdown-icon=none"
        ):
            ui.item(f"About {APP_NAME}", on_click=about_dialog.open).classes("about-command")


def application_status(message: str = "Ready", detail: str = "") -> None:
    """Render the application-wide status bar."""
    with ui.row().classes("app-status-bar w-full gap-1"):
        ui.label(message).classes("status-bar-field grow")
        if detail:
            ui.label(detail).classes("status-bar-field")
