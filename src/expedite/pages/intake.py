"""Order intake form page."""

from datetime import datetime

from nicegui import ui

from expedite.label import render_label
from expedite.local_files import open_local_path
from expedite.models import Order
from expedite.storage.csv_store import (
    append_order,
    get_order,
    next_order_id,
    update_order,
)
from expedite.storage.events import get_event
from expedite.validation import (
    validate_cost,
    validate_name,
    validate_phone,
    validate_work_request,
)


def register_intake_page() -> None:
    def show_event_not_found() -> None:
        with ui.column().classes("w-full max-w-2xl mx-auto p-6 gap-4"):
            ui.label("Event not found").classes("text-2xl font-bold text-negative")
            ui.button("Back to Events", on_click=lambda: ui.navigate.to("/"))

    def render_intake_page(folder_name: str, edit_order_id: int | None = None) -> None:
        event = get_event(folder_name)
        if event is None:
            show_event_not_found()
            return

        existing_order = get_order(event, edit_order_id) if edit_order_id else None
        if edit_order_id is not None and existing_order is None:
            with ui.column().classes("w-full max-w-2xl mx-auto p-6 gap-4"):
                ui.label(f"Order #{edit_order_id} not found").classes(
                    "text-2xl font-bold text-negative"
                )
                ui.button(
                    "Back to Orders",
                    on_click=lambda: ui.navigate.to(f"/events/{folder_name}/orders"),
                )
            return

        ui.page_title(f"{event.name} - Intake")

        with ui.column().classes("w-full max-w-3xl mx-auto p-6 gap-6"):
            with ui.row().classes("w-full items-center justify-between"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(event.name).classes("text-3xl font-bold")
                    ui.button(
                        icon="folder_open",
                        on_click=lambda: open_local_path(event.path),
                    ).props("flat round dense").classes("text-primary").tooltip(str(event.path))
                with ui.row().classes("gap-2"):
                    ui.button(
                        "Orders",
                        on_click=lambda: ui.navigate.to(f"/events/{event.folder_name()}/orders"),
                    ).props("flat")
                    ui.button("Events", on_click=lambda: ui.navigate.to("/")).props("flat")

            warning_box = ui.card().classes("w-full bg-amber-50 hidden")
            with warning_box:
                ui.label("Warnings (submission is still allowed)").classes(
                    "font-semibold text-amber-900"
                )
                warning_list = ui.column().classes("gap-1")

            with ui.card().classes("w-full"):
                current_order_id = (
                    existing_order.order_id if existing_order else next_order_id(event)
                )
                title_prefix = "Edit Order" if existing_order else "Order"
                order_title = ui.label(f"{title_prefix} #{current_order_id}").classes(
                    "text-xl font-semibold"
                )
                name_input = (
                    ui.input(
                        "Name",
                        value=existing_order.name if existing_order else "",
                        validation=validate_name,
                    )
                    .props("outlined debounce=2000")
                    .classes("w-full")
                )
                phone_input = (
                    ui.input(
                        "Phone",
                        value=existing_order.phone if existing_order else "",
                        validation=validate_phone,
                    )
                    .props("outlined debounce=2000")
                    .classes("w-full")
                )
                work_request_input = (
                    ui.textarea(
                        "Work Request",
                        value=existing_order.work_request if existing_order else "",
                        validation=validate_work_request,
                    )
                    .props("outlined debounce=2000")
                    .classes("w-full")
                )
                cost_input = (
                    ui.input(
                        "Cost",
                        value=str(existing_order.cost) if existing_order else "",
                        validation=validate_cost,
                    )
                    .props("outlined debounce=2000")
                    .classes("w-full")
                )
                status_area = ui.column().classes("gap-1")

                def show_warnings(warnings: list[str]) -> None:
                    warning_list.clear()
                    if warnings:
                        warning_box.classes(remove="hidden")
                        with warning_list:
                            for warning in warnings:
                                ui.label(f"• {warning}").classes("text-amber-900")
                    else:
                        warning_box.classes(add="hidden")

                def clear_form() -> None:
                    fields = (name_input, phone_input, work_request_input, cost_input)
                    for field in fields:
                        field.value = ""
                        field.error = None

                def handle_submit() -> None:
                    order = Order.model_construct(
                        order_id=existing_order.order_id
                        if existing_order
                        else next_order_id(event),
                        timestamp=existing_order.timestamp
                        if existing_order
                        else datetime.now().astimezone(),
                        event=event,
                        name=name_input.value,
                        phone=phone_input.value,
                        work_request=work_request_input.value,
                        cost=cost_input.value,
                    )

                    label_path = render_label(order)
                    saved_order = order.with_label_filename(label_path.name)
                    if existing_order:
                        update_order(saved_order)
                    else:
                        append_order(saved_order)

                    status_area.clear()
                    with status_area, ui.row().classes("items-center gap-2"):
                        verb = "Updated" if existing_order else "Saved"
                        ui.label(f"{verb} order #{saved_order.order_id}").classes("text-positive")
                        ui.button(
                            icon="article",
                            on_click=lambda path=label_path: open_local_path(path),
                        ).props("flat round dense").classes("text-primary").tooltip(str(label_path))
                    notify_verb = "Updated" if existing_order else "Saved"
                    ui.notify(
                        f"{notify_verb} order #{saved_order.order_id}",
                        type="positive",
                    )
                    if not existing_order:
                        clear_form()
                        order_title.text = f"Order #{next_order_id(event)}"

                submit_text = "Save Changes" if existing_order else "Submit Order"
                ui.button(submit_text, on_click=handle_submit).props("color=primary size=lg")

    @ui.page("/events/{folder_name}")
    def intake_page(folder_name: str) -> None:
        render_intake_page(folder_name)

    @ui.page("/events/{folder_name}/orders/{order_id}/edit")
    def edit_order_page(folder_name: str, order_id: int) -> None:
        render_intake_page(folder_name, order_id)
