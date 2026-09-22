"""Reusable classic desktop UI components."""

import base64
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from nicegui import events, ui
from nicegui.element import Element
from nicegui.elements.button import Button
from nicegui.elements.dialog import Dialog

from expedite.config import (
    APP_NAME,
    MAX_LABEL_NOTES_HEIGHT_MM,
    PRINTER_NAME,
    data_dir,
)
from expedite.local_files import open_local_path
from expedite.storage.settings import (
    MAX_LOGO_BYTES,
    receipt_settings,
    save_receipt_settings,
    validate_receipt_logo_png,
)


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


def enable_list_keyboard(list_element: Element) -> None:
    """Enable classic Up/Down selection and Enter activation on a list table."""
    list_element.props("tabindex=0")
    list_element.on(
        "click",
        js_handler="(event) => event.currentTarget.focus()",
    )
    list_element.on(
        "keydown",
        js_handler="""
        (event) => {
            if (event.target !== event.currentTarget) return;
            const rows = [...event.currentTarget.querySelectorAll('.classic-list-row')];
            if (!rows.length) return;
            const selectedIndex = rows.findIndex(row => row.classList.contains('is-selected'));
            if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                const offset = event.key === 'ArrowDown' ? 1 : -1;
                const fallback = event.key === 'ArrowDown' ? 0 : rows.length - 1;
                const nextIndex = selectedIndex < 0
                    ? fallback
                    : Math.min(Math.max(selectedIndex + offset, 0), rows.length - 1);
                rows[nextIndex].click();
                rows[nextIndex].scrollIntoView({block: 'nearest'});
            } else if (event.key === 'Enter' && selectedIndex >= 0) {
                event.preventDefault();
                rows[selectedIndex].dispatchEvent(new MouseEvent('dblclick', {
                    bubbles: true,
                    cancelable: true,
                }));
            }
        }
        """,
    )


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
    on_accept: Callable[[], object] | None = None,
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


def receipt_settings_dialog() -> Callable[[], None]:
    """Create the shared Receipt Settings dialog and return its open command."""
    saved_settings = receipt_settings()
    pending_logo = saved_settings.logo_png
    pending_filename = "receipt-logo.png" if pending_logo is not None else ""

    def update_logo_controls() -> None:
        filename_input.value = pending_filename
        remove_button.set_enabled(pending_logo is not None)
        logo_preview.refresh()

    def remove_logo() -> None:
        nonlocal pending_logo, pending_filename
        pending_logo = None
        pending_filename = ""
        update_logo_controls()

    async def upload_logo(event: events.UploadEventArguments) -> None:
        nonlocal pending_logo, pending_filename
        data = await event.file.read()
        try:
            validate_receipt_logo_png(data)
        except ValueError as error:
            ui.notify(str(error), type="negative")
            return
        pending_logo = data
        pending_filename = event.file.name
        logo_upload.reset()
        update_logo_controls()

    def adjust_notes_height(amount: float) -> None:
        try:
            current = float(notes_height_input.value or 0)
        except (TypeError, ValueError):
            current = 0
        value = min(max(current + amount, 0), MAX_LABEL_NOTES_HEIGHT_MM)
        notes_height_input.value = int(value) if value.is_integer() else value

    def save_settings() -> None:
        name = (receipt_name_input.value or "").strip()
        if not name:
            ui.notify("Receipt name cannot be empty.", type="negative")
            receipt_name_input.run_method("focus")
            return
        try:
            notes_height = float(notes_height_input.value or 0)
            save_receipt_settings(
                name=name,
                notes_height_mm=notes_height,
                logo_png=pending_logo,
            )
        except (TypeError, ValueError) as error:
            ui.notify(str(error), type="negative")
            notes_height_input.run_method("focus")
            return
        update_application_status("Receipt settings saved", name)
        settings_dialog.close()

    with classic_dialog(
        "Receipt Settings",
        on_accept=save_settings,
        width="600px",
    ) as settings_dialog:
        with group_box("General"):
            with labeled_field("Receipt name"):
                receipt_name_input = ui.input().props("outlined maxlength=60").classes("w-full")
            with labeled_field("Printer"):
                ui.input(value=PRINTER_NAME).props("outlined readonly").classes("w-full")

        with group_box("Logo"):
            logo_upload = (
                ui.upload(
                    auto_upload=True,
                    max_file_size=MAX_LOGO_BYTES,
                    on_upload=upload_logo,
                    on_rejected=lambda: ui.notify(
                        "Logo must be a PNG file no larger than 5 MB.",
                        type="negative",
                    ),
                )
                .props("accept=.png")
                .classes("hidden")
            )
            with (
                labeled_field("File"),
                ui.row().classes("w-full items-center gap-2 flex-nowrap"),
            ):
                filename_input = ui.input().props("outlined readonly").classes("grow min-w-0")
                browse_button = ui.button("Browse...").props("flat")
                remove_button = ui.button("Remove", on_click=remove_logo).props("flat")
            browse_button.on(
                "click",
                js_handler=(
                    "() => document.getElementById('"
                    f"{logo_upload.html_id}"
                    "')?.querySelector('input[type=file]')?.click()"
                ),
            )

            @ui.refreshable
            def logo_preview() -> None:
                with ui.element("div").classes(
                    "classic-logo-preview w-full flex items-center justify-center"
                ):
                    if pending_logo is None:
                        ui.label("No receipt logo configured").classes("text-sm text-gray-500")
                    else:
                        encoded = base64.b64encode(pending_logo).decode("ascii")
                        ui.image(f"data:image/png;base64,{encoded}").props("fit=contain").classes(
                            "w-full"
                        )

            logo_preview()

        with (
            group_box("Layout"),
            labeled_field("Notes height"),
            ui.row().classes("classic-number-control w-full items-stretch gap-0 flex-nowrap"),
        ):
            notes_height_input = (
                ui.number(
                    min=0,
                    max=MAX_LABEL_NOTES_HEIGHT_MM,
                    step=5,
                )
                .props("outlined suffix=mm")
                .classes("grow min-w-0 classic-number-input")
            )
            with ui.column().classes("classic-spin-control gap-0"):
                ui.button("▲", on_click=lambda: adjust_notes_height(5)).props(
                    'flat dense aria-label="Increase notes height"'
                ).classes("classic-spin-button")
                ui.button("▼", on_click=lambda: adjust_notes_height(-5)).props(
                    'flat dense aria-label="Decrease notes height"'
                ).classes("classic-spin-button")
        settings_dialog.set_initial_focus(receipt_name_input)

    def open_settings() -> None:
        nonlocal pending_logo, pending_filename
        current = receipt_settings()
        receipt_name_input.value = current.name
        notes_height_input.value = current.notes_height_mm
        pending_logo = current.logo_png
        pending_filename = "receipt-logo.png" if pending_logo is not None else ""
        logo_upload.reset()
        update_logo_controls()
        settings_dialog.open()

    return open_settings


def application_menu(*, on_export: Callable[[], None] | None = None) -> None:
    """Render the application-wide menu bar."""
    open_receipt_settings = receipt_settings_dialog()
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
