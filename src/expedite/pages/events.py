"""Events landing page."""

import base64
from datetime import datetime

from nicegui import events as ui_events
from nicegui import ui

from expedite.config import APP_NAME, MAX_LABEL_NOTES_HEIGHT_MM, PRINTER_NAME, data_dir
from expedite.local_files import open_local_path
from expedite.storage.events import create_event, list_events
from expedite.storage.settings import (
    MAX_LOGO_BYTES,
    receipt_settings,
    save_receipt_settings,
    validate_receipt_logo_png,
)
from expedite.theme import apply_windows_98_theme


def register_events_page() -> None:
    @ui.page("/")
    def events_page() -> None:
        apply_windows_98_theme()
        ui.page_title(APP_NAME)

        with ui.column().classes("app-page w-full p-6 gap-6"):
            app_data_dir = data_dir()

            current_settings = receipt_settings()
            pending_logo = current_settings.logo_png
            with ui.dialog() as settings_dialog, ui.card().classes("w-full max-w-md"):
                ui.label("Receipt Settings").classes("text-xl font-semibold")
                ui.label(f"Printer: {PRINTER_NAME}").classes("text-sm text-gray-600")
                receipt_name_input = (
                    ui.input("Receipt name", value=current_settings.name)
                    .props("outlined maxlength=60")
                    .classes("w-full")
                )
                notes_height_input = (
                    ui.number(
                        "Blank Notes area height",
                        value=current_settings.notes_height_mm,
                        min=0,
                        max=MAX_LABEL_NOTES_HEIGHT_MM,
                        step=5,
                    )
                    .props("outlined suffix=mm")
                    .classes("w-full")
                )

                @ui.refreshable
                def logo_preview() -> None:
                    if pending_logo is None:
                        ui.label("No receipt logo configured").classes("text-sm text-gray-500")
                        return
                    encoded = base64.b64encode(pending_logo).decode("ascii")
                    ui.image(f"data:image/png;base64,{encoded}").classes(
                        "w-full max-h-40 object-contain border rounded"
                    )

                    def remove_logo() -> None:
                        nonlocal pending_logo
                        pending_logo = None
                        logo_preview.refresh()

                    ui.button("Remove logo", icon="delete", on_click=remove_logo).props(
                        "flat color=negative"
                    )

                logo_preview()

                async def upload_logo(event: ui_events.UploadEventArguments) -> None:
                    nonlocal pending_logo
                    data = await event.file.read()
                    try:
                        validate_receipt_logo_png(data)
                    except ValueError as error:
                        ui.notify(str(error), type="negative")
                        return
                    pending_logo = data
                    logo_preview.refresh()
                    logo_upload.reset()

                logo_upload = (
                    ui.upload(
                        label="Upload PNG logo",
                        auto_upload=True,
                        max_file_size=MAX_LOGO_BYTES,
                        on_upload=upload_logo,
                        on_rejected=lambda: ui.notify(
                            "Logo must be a PNG file no larger than 5 MB.", type="negative"
                        ),
                    )
                    .props("accept=.png")
                    .classes("w-full")
                )

                def save_settings() -> None:
                    try:
                        save_receipt_settings(
                            name=receipt_name_input.value or "",
                            notes_height_mm=float(notes_height_input.value or 0),
                            logo_png=pending_logo,
                        )
                    except ValueError as error:
                        ui.notify(str(error), type="negative")
                        return
                    settings_dialog.close()
                    ui.notify("Receipt settings saved", type="positive")

                with ui.row().classes("justify-end gap-2"):
                    ui.button("Cancel", on_click=settings_dialog.close).props("flat")
                    ui.button("Save", on_click=save_settings).props("color=primary")

            def open_settings() -> None:
                nonlocal pending_logo
                saved_settings = receipt_settings()
                receipt_name_input.value = saved_settings.name
                notes_height_input.value = saved_settings.notes_height_mm
                pending_logo = saved_settings.logo_png
                logo_preview.refresh()
                logo_upload.reset()
                settings_dialog.open()

            with ui.row().classes("app-page-header w-full items-center justify-between"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(APP_NAME).classes("app-page-title text-3xl font-bold")
                    ui.button(
                        icon="folder_open",
                        on_click=lambda: open_local_path(app_data_dir),
                    ).props("flat round dense").classes("text-primary").tooltip(str(app_data_dir))
                with ui.row().classes("items-center gap-1"):
                    ui.button(
                        icon="settings",
                        on_click=open_settings,
                    ).props("flat round").tooltip("Receipt settings")
                    ui.button("Catalog", on_click=lambda: ui.navigate.to("/catalog")).props("flat")

            with ui.card().classes("w-full"):
                ui.label("Create New Event").classes("text-xl font-semibold")
                name_input = ui.input("Event name").props("outlined").classes("w-full")
                today = datetime.now().astimezone().date().isoformat()
                date_input = (
                    ui.input("Start date", value=today)
                    .props("outlined type=date")
                    .classes("w-full")
                )

                def handle_create() -> None:
                    event = create_event(
                        name_input.value or "Untitled Event", date_input.value or None
                    )
                    ui.navigate.to(f"/events/{event.folder_name()}")

                ui.button("Create New", on_click=handle_create).props("color=primary")

            with ui.card().classes("w-full"):
                ui.label("Recent Events").classes("text-xl font-semibold")
                events = list_events()
                if not events:
                    ui.label("No events yet. Create one above to begin.").classes("text-gray-500")
                else:
                    for event in events:
                        with ui.row().classes("w-full items-center justify-between border-b py-2"):
                            with ui.column().classes("gap-0"):
                                ui.link(
                                    event.name,
                                    f"/events/{event.folder_name()}/manage",
                                ).classes("font-medium text-primary no-underline")
                                ui.label(f"{event.start_date} · {event.folder_name()}").classes(
                                    "text-sm text-gray-500"
                                )
                            with ui.row().classes("gap-2"):
                                ui.button(
                                    "Intake",
                                    on_click=lambda e=event: ui.navigate.to(
                                        f"/events/{e.folder_name()}"
                                    ),
                                )
                                ui.button(
                                    "Orders",
                                    on_click=lambda e=event: ui.navigate.to(
                                        f"/events/{e.folder_name()}/orders"
                                    ),
                                ).props("flat")
