"""Order listing page for an event."""

from datetime import datetime
from pathlib import Path

from nicegui import run, ui

from expedite.config import PRINTER_NAME
from expedite.local_files import open_local_path
from expedite.printing import PrintError, print_label
from expedite.storage.events import get_event
from expedite.storage.sqlite_store import export_orders_csv, list_order_records
from expedite.theme import apply_windows_98_theme


def display_timestamp(value: datetime) -> str:
    return value.astimezone().isoformat(timespec="minutes").replace("T", " ")


def register_orders_page() -> None:
    @ui.page("/events/{folder_name}/orders")
    def orders_page(folder_name: str) -> None:
        apply_windows_98_theme()
        event = get_event(folder_name)
        if event is None:
            with ui.column().classes("win98-window w-full max-w-2xl mx-auto p-6 gap-4"):
                ui.label("Event not found").classes("text-2xl font-bold text-negative")
                ui.button("Back to Events", on_click=lambda: ui.navigate.to("/"))
            return

        ui.page_title(f"{event.name} - Orders")
        orders = list_order_records(event)

        async def print_label_image(path: Path) -> None:
            try:
                printer_name = await run.io_bound(print_label, path)
            except PrintError as error:
                ui.notify(str(error), type="negative", multi_line=True)
            else:
                ui.notify(f"Sent label to {printer_name}", type="positive")

        with ui.column().classes("win98-window w-full max-w-6xl mx-auto p-6 gap-6"):
            with ui.row().classes("win98-title-bar w-full items-center justify-between"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(f"{event.name} Orders").classes(
                        "win98-title-bar-text text-3xl font-bold"
                    )
                    ui.button(
                        icon="folder_open",
                        on_click=lambda: open_local_path(event.path),
                    ).props("flat round dense").classes("text-primary").tooltip(str(event.path))
                with ui.row().classes("gap-2"):

                    def handle_export() -> None:
                        path = export_orders_csv(event)
                        ui.notify(f"Exported orders to {path.name}", type="positive")

                    ui.button(
                        "Export to CSV",
                        icon="download",
                        on_click=handle_export,
                    ).props("flat")
                    ui.button(
                        "Manage",
                        on_click=lambda: ui.navigate.to(f"/events/{event.folder_name()}/manage"),
                    ).props("flat")
                    ui.button(
                        "Intake",
                        on_click=lambda: ui.navigate.to(f"/events/{event.folder_name()}"),
                    ).props("flat")
                    ui.button("Events", on_click=lambda: ui.navigate.to("/")).props("flat")

            if not orders:
                with ui.card().classes("w-full"):
                    ui.label("No orders yet.").classes("text-gray-500")
                return

            with ui.card().classes("w-full"):
                ui.label(f"{len(orders)} order(s)").classes("text-xl font-semibold")
                with ui.row().classes("w-full font-semibold border-b pb-2 items-center text-sm"):
                    ui.label("ID").classes("w-16")
                    ui.label("Submitted").classes("w-44")
                    ui.label("Name").classes("w-40")
                    ui.label("Phone").classes("w-40")
                    ui.label("Work Request").classes("grow")
                    ui.label("Cost").classes("w-24")
                    ui.label("Label").classes("w-24")

                for order in orders:
                    label_filename = order.label_filename or ""
                    label_path = event.path / "labels" / label_filename
                    with ui.row().classes("w-full border-b py-2 items-center text-sm gap-2"):
                        with ui.row().classes("w-16 items-center gap-1"):
                            ui.label(str(order.order_id))
                            ui.button(
                                icon="edit",
                                on_click=lambda order_id=order.order_id: ui.navigate.to(
                                    f"/events/{event.folder_name()}/orders/{order_id}/edit"
                                ),
                            ).props("flat round dense").classes("text-primary").tooltip(
                                "Edit order"
                            )
                        ui.label(display_timestamp(order.timestamp)).classes("w-44")
                        ui.label(order.name).classes("w-40")
                        ui.label(order.phone).classes("w-40")
                        ui.label(order.work_request).classes("grow")
                        ui.label(order.cost).classes("w-24")
                        with ui.row().classes("w-24 gap-0"):
                            if label_filename:
                                ui.button(
                                    icon="article",
                                    on_click=lambda path=label_path: open_local_path(path),
                                ).props("flat round dense").classes("text-primary").tooltip(
                                    str(label_path)
                                )
                                ui.button(
                                    icon="print",
                                    on_click=lambda path=label_path: print_label_image(path),
                                ).props("flat round dense").classes("text-primary").tooltip(
                                    f"Print on {PRINTER_NAME}"
                                )
                            else:
                                ui.label("—").classes("text-gray-400")
