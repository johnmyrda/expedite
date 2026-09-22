"""Order listing page for an event."""

from datetime import datetime
from pathlib import Path

from nicegui import run, ui

from expedite.config import PRINTER_NAME
from expedite.local_files import open_local_path
from expedite.pages.components import application_menu, application_status
from expedite.pages.navigation import event_navigation_tabs
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
            with ui.column().classes("app-page w-full p-6 gap-4"):
                application_menu()
                ui.label("Event not found").classes("text-2xl font-bold text-negative")
                ui.button("Back to Events", on_click=lambda: ui.navigate.to("/"))
                application_status("Event not found")
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

        def handle_export() -> None:
            path = export_orders_csv(event)
            ui.notify(f"Exported orders to {path.name}", type="positive")

        with ui.column().classes("app-page w-full p-6 gap-6"):
            application_menu(on_export=handle_export)
            with ui.row().classes("app-page-header w-full items-center justify-between"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(f"{event.name} Orders").classes("app-page-title text-3xl font-bold")
                    ui.button(
                        icon="folder_open",
                        on_click=lambda: open_local_path(event.path),
                    ).props("flat round dense").classes("text-primary").tooltip(str(event.path))

            event_navigation_tabs(event.folder_name(), "orders")

            with ui.element("div").classes("classic-list-panel"):
                with ui.element("table").classes("classic-list order-list"):
                    with ui.element("thead"):
                        with ui.element("tr"):
                            for heading, width in (
                                ("ID", "70px"),
                                ("Submitted", "170px"),
                                ("Name", "150px"),
                                ("Phone", "150px"),
                                ("Work Request", "auto"),
                                ("Cost", "90px"),
                                ("Actions", "220px"),
                            ):
                                with ui.element("th").style(f"width: {width}"):
                                    ui.label(heading)
                    with ui.element("tbody"):
                        if not orders:
                            with ui.element("tr"):
                                with ui.element("td").props("colspan=7"):
                                    ui.label("No orders yet.").classes("text-gray-500")

                        for order in orders:
                            label_filename = order.label_filename or ""
                            label_path = event.path / "labels" / label_filename
                            with ui.element("tr"):
                                with ui.element("td"):
                                    ui.label(str(order.order_id))
                                with ui.element("td"):
                                    ui.label(display_timestamp(order.timestamp))
                                with ui.element("td"):
                                    ui.label(order.name)
                                with ui.element("td"):
                                    ui.label(order.phone)
                                with ui.element("td"):
                                    ui.label(order.work_request)
                                with ui.element("td"):
                                    ui.label(order.cost)
                                with ui.element("td").classes("classic-actions"):
                                    with ui.row().classes("gap-1 items-center"):
                                        ui.button(
                                            "Edit...",
                                            on_click=lambda order_id=order.order_id: ui.navigate.to(
                                                f"/events/{event.folder_name()}/orders/"
                                                f"{order_id}/edit"
                                            ),
                                        ).props("flat dense")
                                        if label_filename:
                                            ui.button(
                                                "Open",
                                                on_click=lambda path=label_path: open_local_path(
                                                    path
                                                ),
                                            ).props("flat dense").tooltip(str(label_path))
                                            ui.button(
                                                "Print",
                                                on_click=lambda path=label_path: print_label_image(
                                                    path
                                                ),
                                            ).props("flat dense").tooltip(
                                                f"Print on {PRINTER_NAME}"
                                            )

            application_status("Ready", f"{len(orders)} order(s)")
