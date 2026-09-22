"""Order listing page for an event."""

from datetime import datetime
from pathlib import Path

from nicegui import run, ui

from expedite.config import PRINTER_NAME
from expedite.local_files import open_local_path
from expedite.models import OrderRecord
from expedite.pages.components import (
    application_menu,
    application_status,
    enable_list_keyboard,
    group_box,
    sortable_header,
    update_application_status,
)
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
        state: dict[str, int | str | bool | None] = {
            "selected_order_id": None,
            "sort_key": "order_id",
            "sort_descending": True,
        }

        def sorted_orders() -> list[OrderRecord]:
            def cost_value(order: OrderRecord) -> float:
                try:
                    return float(order.cost)
                except (TypeError, ValueError):
                    return 0

            key = str(state["sort_key"])
            key_functions = {
                "order_id": lambda order: order.order_id,
                "timestamp": lambda order: order.timestamp.timestamp(),
                "name": lambda order: order.name.casefold(),
                "phone": lambda order: order.phone,
                "work_request": lambda order: order.work_request.casefold(),
                "cost": cost_value,
            }
            return sorted(
                orders,
                key=key_functions[key],
                reverse=bool(state["sort_descending"]),
            )

        async def print_label_image(path: Path) -> None:
            try:
                printer_name = await run.io_bound(print_label, path)
            except PrintError as error:
                ui.notify(str(error), type="negative", multi_line=True)
            else:
                update_application_status("Label sent to printer", printer_name)

        def handle_export() -> None:
            path = export_orders_csv(event)
            update_application_status("Orders exported", path.name)

        def edit_order(order_id: int) -> None:
            ui.navigate.to(f"/events/{event.folder_name()}/orders/{order_id}/edit")

        with ui.column().classes("app-page w-full p-6 gap-6"):
            application_menu(on_export=handle_export)
            with (
                ui.row().classes("app-page-header w-full items-center justify-between"),
                ui.row().classes("items-center gap-2"),
            ):
                ui.label(f"{event.name} Orders").classes("app-page-title text-3xl font-bold")
                ui.button(
                    icon="folder_open",
                    on_click=lambda: open_local_path(event.path),
                ).props("flat round dense").classes("text-primary").tooltip(str(event.path))

            event_navigation_tabs(event.folder_name(), "orders")

            def selected_order() -> OrderRecord | None:
                return next(
                    (order for order in orders if order.order_id == state["selected_order_id"]),
                    None,
                )

            def selected_receipt_path() -> Path | None:
                order = selected_order()
                return (
                    event.path / "labels" / order.label_filename
                    if order is not None and order.label_filename
                    else None
                )

            @ui.refreshable
            def order_status() -> None:
                order = selected_order()
                detail = (
                    f"Order #{order.order_id} selected · {len(orders)} order(s)"
                    if order is not None
                    else f"{len(orders)} order(s)"
                )
                application_status("Ready", detail)

            @ui.refreshable
            def order_list() -> None:
                row_elements = {}

                def configure_toolbar() -> None:
                    order = selected_order()
                    receipt_path = selected_receipt_path()
                    edit_button.enabled = order is not None
                    open_button.enabled = receipt_path is not None
                    print_button.enabled = receipt_path is not None
                    if receipt_path is not None:
                        open_button.tooltip(str(receipt_path))
                        print_button.tooltip(f"Print on {PRINTER_NAME}")

                def select_order(order_id: int) -> None:
                    previous_id = state["selected_order_id"]
                    if previous_id in row_elements:
                        row_elements[previous_id].classes(remove="is-selected")
                    state["selected_order_id"] = order_id
                    row_elements[order_id].classes(add="is-selected")
                    configure_toolbar()
                    order_status.refresh()

                def edit_selected_order() -> None:
                    order = selected_order()
                    if order is not None:
                        edit_order(order.order_id)

                def open_selected_receipt() -> None:
                    receipt_path = selected_receipt_path()
                    if receipt_path is not None:
                        open_local_path(receipt_path)

                async def print_selected_receipt() -> None:
                    receipt_path = selected_receipt_path()
                    if receipt_path is not None:
                        await print_label_image(receipt_path)

                with ui.row().classes("classic-list-toolbar w-full items-center gap-1"):
                    edit_button = ui.button("Edit...", on_click=edit_selected_order).props(
                        "flat dense"
                    )
                    open_button = ui.button("Open Receipt", on_click=open_selected_receipt).props(
                        "flat dense"
                    )
                    print_button = ui.button("Print", on_click=print_selected_receipt).props(
                        "flat dense"
                    )
                    ui.element("div").classes("classic-toolbar-separator")
                    ui.button("Export...", on_click=handle_export).props("flat dense")
                    configure_toolbar()

                def change_sort(key: str) -> None:
                    if state["sort_key"] == key:
                        state["sort_descending"] = not bool(state["sort_descending"])
                    else:
                        state["sort_key"] = key
                        state["sort_descending"] = False
                    order_list.refresh()

                with (
                    ui.element("div").classes("classic-list-panel"),
                    ui.element("table")
                    .classes("classic-list order-list")
                    .props('aria-label="Orders"') as order_table,
                ):
                    enable_list_keyboard(order_table)
                    with ui.element("thead"), ui.element("tr"):
                        for heading, key, width in (
                            ("ID", "order_id", "70px"),
                            ("Submitted", "timestamp", "180px"),
                            ("Name", "name", "180px"),
                            ("Phone", "phone", "170px"),
                            ("Work Request", "work_request", "auto"),
                            ("Cost", "cost", "110px"),
                        ):
                            with ui.element("th").style(f"width: {width}"):
                                sortable_header(
                                    heading,
                                    active=state["sort_key"] == key,
                                    descending=bool(state["sort_descending"]),
                                    on_click=lambda sort_key=key: change_sort(sort_key),
                                )
                    with ui.element("tbody"):
                        if not orders:
                            with (
                                ui.element("tr"),
                                ui.element("td").props("colspan=6"),
                            ):
                                ui.label("No orders yet.").classes("text-gray-500")

                        for order in sorted_orders():
                            selected = order.order_id == state["selected_order_id"]
                            row = ui.element("tr").classes(
                                "classic-list-row" + (" is-selected" if selected else "")
                            )
                            row_elements[order.order_id] = row
                            row.on(
                                "click",
                                lambda order_id=order.order_id: select_order(order_id),
                            ).on(
                                "dblclick",
                                lambda order_id=order.order_id: edit_order(order_id),
                            )
                            with row:
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

            with group_box("Event Orders"):
                order_list()
            order_status()
