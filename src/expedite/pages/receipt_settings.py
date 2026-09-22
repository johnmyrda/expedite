"""Receipt-settings dialog and its local interaction behavior."""

import base64
from collections.abc import Callable

from nicegui import events, ui

from expedite.config import MAX_LABEL_NOTES_HEIGHT_MM, PRINTER_NAME
from expedite.pages.classic_ui import classic_dialog, group_box, labeled_field
from expedite.storage.settings import (
    MAX_LOGO_BYTES,
    receipt_settings,
    save_receipt_settings,
    validate_receipt_logo_png,
)

StatusUpdater = Callable[[str, str | None], None]


def receipt_settings_dialog(*, on_saved: StatusUpdater) -> Callable[[], None]:
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

    def adjust_notes_height(amount: int) -> None:
        try:
            current = round(float(notes_height_input.value or 0))
        except (TypeError, ValueError):
            current = 0
        notes_height_input.value = min(max(current + amount, 0), MAX_LABEL_NOTES_HEIGHT_MM)

    def save_settings() -> None:
        name = (receipt_name_input.value or "").strip()
        if not name:
            ui.notify("Receipt name cannot be empty.", type="negative")
            receipt_name_input.run_method("focus")
            return
        try:
            raw_notes_height = float(notes_height_input.value or 0)
            if not raw_notes_height.is_integer():
                raise ValueError("Notes height must be a whole number of millimeters.")
            notes_height = int(raw_notes_height)
            save_receipt_settings(
                name=name,
                notes_height_mm=notes_height,
                logo_png=pending_logo,
            )
        except (TypeError, ValueError) as error:
            ui.notify(str(error), type="negative")
            notes_height_input.run_method("focus")
            return
        on_saved("Receipt settings saved", name)
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
                ui.row().classes("classic-file-row w-full items-center gap-2 flex-nowrap"),
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
