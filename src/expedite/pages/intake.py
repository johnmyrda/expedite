"""Order intake form page."""

from nicegui import ui

from expedite.label import render_label
from expedite.local_files import open_local_path
from expedite.models import Order
from expedite.storage.csv_store import append_order, next_order_id
from expedite.storage.events import get_event


def register_intake_page() -> None:
    @ui.page("/events/{folder_name}")
    def intake_page(folder_name: str) -> None:
        event = get_event(folder_name)
        if event is None:
            with ui.column().classes("w-full max-w-2xl mx-auto p-6 gap-4"):
                ui.label("Event not found").classes("text-2xl font-bold text-negative")
                ui.button("Back to Events", on_click=lambda: ui.navigate.to("/"))
            return

        ui.page_title(f"{event.name} - Intake")

        with ui.column().classes("w-full max-w-3xl mx-auto p-6 gap-6"):
            with ui.row().classes("w-full items-center justify-between"):
                with ui.row().classes("items-center gap-2"):
                    ui.label(event.name).classes("text-3xl font-bold")
                    ui.button(
                        icon="folder_open",
                        on_click=lambda: open_local_path(event.path),
                    ).props("flat round dense").classes("text-primary").tooltip(
                        str(event.path)
                    )
                ui.button("Events", on_click=lambda: ui.navigate.to("/")).props("flat")

            warning_box = ui.card().classes("w-full bg-amber-50 hidden")
            with warning_box:
                ui.label("Warnings (submission is still allowed)").classes(
                    "font-semibold text-amber-900"
                )
                warning_list = ui.column().classes("gap-1")

            with ui.card().classes("w-full"):
                order_title = ui.label(f"Order #{next_order_id(event)}").classes(
                    "text-xl font-semibold"
                )
                name_input = ui.input("Name").props("outlined").classes("w-full")
                phone_input = ui.input("Phone").props("outlined").classes("w-full")
                work_request_input = (
                    ui.textarea("Work Request").props("outlined").classes("w-full")
                )
                cost_input = ui.input("Cost").props("outlined").classes("w-full")
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
                    name_input.value = ""
                    phone_input.value = ""
                    work_request_input.value = ""
                    cost_input.value = ""

                def handle_submit() -> None:
                    order_id = next_order_id(event)
                    order = Order.model_construct(
                        order_id=order_id,
                        event=event,
                        name=name_input.value,
                        phone=phone_input.value,
                        work_request=work_request_input.value,
                        cost=cost_input.value,
                    )

                    label_path = render_label(order)
                    saved_order = order.with_label_filename(label_path.name)
                    append_order(saved_order)

                    status_area.clear()
                    with status_area, ui.row().classes("items-center gap-2"):
                        ui.label(f"Saved order #{saved_order.order_id}").classes(
                            "text-positive"
                        )
                        ui.button(
                            icon="article",
                            on_click=lambda path=label_path: open_local_path(path),
                        ).props("flat round dense").classes("text-primary").tooltip(
                            str(label_path)
                        )
                    ui.notify(f"Saved order #{saved_order.order_id}", type="positive")
                    clear_form()
                    order_title.text = f"Order #{next_order_id(event)}"

                ui.button("Submit Order", on_click=handle_submit).props(
                    "color=primary size=lg"
                )
