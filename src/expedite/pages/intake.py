"""Order intake form page."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from nicegui import events, run, ui

from expedite.config import PRINTER_NAME
from expedite.label import render_label
from expedite.local_files import open_local_path
from expedite.models import Order, OrderLine
from expedite.money import display_price, parse_price_cents
from expedite.pages.components import (
    application_menu,
    application_status,
    classic_dialog,
    group_box,
    labeled_field,
)
from expedite.pages.navigation import event_navigation_tabs
from expedite.printing import PrintError, print_label
from expedite.storage.events import get_event
from expedite.storage.sqlite_store import (
    append_order,
    event_catalog_prices,
    get_order,
    list_catalog_favorite_ids,
    list_catalog_items,
    next_order_id,
    update_order,
)
from expedite.theme import apply_windows_98_theme
from expedite.validation import validate_name, validate_phone


@dataclass
class LineDraft:
    catalog_item_id: int | None = None
    description: str = ""
    quantity: int = 1
    unit_price: str = ""
    notes: str = ""
    show_notes: bool = False


def register_intake_page() -> None:
    def show_event_not_found() -> None:
        with ui.column().classes("app-page w-full p-6 gap-4"):
            application_menu()
            ui.label("Event not found").classes("text-2xl font-bold text-negative")
            ui.button("Back to Events", on_click=lambda: ui.navigate.to("/"))
            application_status("Event not found")

    def render_intake_page(folder_name: str, edit_order_id: int | None = None) -> None:
        apply_windows_98_theme()
        event = get_event(folder_name)
        if event is None:
            show_event_not_found()
            return

        existing_order = get_order(event, edit_order_id) if edit_order_id else None
        if edit_order_id is not None and existing_order is None:
            with ui.column().classes("app-page w-full p-6 gap-4"):
                application_menu()
                ui.label(f"Order #{edit_order_id} not found").classes(
                    "text-2xl font-bold text-negative"
                )
                ui.button(
                    "Back to Orders",
                    on_click=lambda: ui.navigate.to(f"/events/{folder_name}/orders"),
                )
                application_status("Order not found")
            return

        catalog = list_catalog_items()
        catalog_by_id = {item.id: item for item in catalog if item.id is not None}
        overrides = event_catalog_prices(event)
        catalog_options = {0: "Freeform item"}
        catalog_options.update(
            {item_id: item.name for item_id, item in catalog_by_id.items() if item.active}
        )
        favorite_ids = set(list_catalog_favorite_ids())
        favorite_items = [
            item
            for item in catalog
            if item.id in favorite_ids and item.active and item.id is not None
        ]

        if existing_order and existing_order.line_items:
            line_drafts = [
                LineDraft(
                    catalog_item_id=line.catalog_item_id,
                    description=line.description,
                    quantity=line.quantity,
                    unit_price=f"{line.unit_price_cents / 100:.2f}",
                    notes=line.notes or "",
                    show_notes=bool(line.notes),
                )
                for line in existing_order.line_items
            ]
            for line in existing_order.line_items:
                if line.catalog_item_id and line.catalog_item_id not in catalog_options:
                    item = catalog_by_id.get(line.catalog_item_id)
                    if item:
                        catalog_options[line.catalog_item_id] = item.name
        elif existing_order:
            line_drafts = [
                LineDraft(
                    description=existing_order.work_request,
                    unit_price=str(existing_order.cost),
                )
            ]
        else:
            line_drafts = [LineDraft()]

        ui.page_title(f"{event.name} - Intake")

        async def print_label_image(path: Path) -> None:
            try:
                printer_name = await run.io_bound(print_label, path)
            except PrintError as error:
                ui.notify(str(error), type="negative", multi_line=True)
            else:
                ui.notify(f"Sent label to {printer_name}", type="positive")

        with ui.column().classes("app-page w-full p-6 gap-6"):
            application_menu()
            with (
                ui.row().classes("app-page-header w-full items-center justify-between"),
                ui.row().classes("items-center gap-2"),
            ):
                ui.label(event.name).classes("app-page-title text-3xl font-bold")
                ui.button(
                    icon="folder_open",
                    on_click=lambda: open_local_path(event.path),
                ).props("flat round dense").classes("text-primary").tooltip(str(event.path))

            event_navigation_tabs(event.folder_name(), "intake")

            warning_box = ui.card().classes("w-full bg-amber-50 hidden")
            with warning_box:
                ui.label("Warnings (submission is still allowed)").classes(
                    "font-semibold text-amber-900"
                )
                warning_list = ui.column().classes("gap-1")

            with group_box("Order Intake"):
                current_order_id = (
                    existing_order.order_id if existing_order else next_order_id(event)
                )
                title_prefix = "Edit Order" if existing_order else "Order"
                order_title = ui.label(f"{title_prefix} #{current_order_id}").classes(
                    "text-xl font-semibold"
                )
                with group_box("Customer Information"):
                    with labeled_field("Name"):
                        name_input = (
                            ui.input(
                                value=existing_order.name if existing_order else "",
                                validation=validate_name,
                            )
                            .props("outlined debounce=2000")
                            .classes("w-full")
                        )
                    with labeled_field("Phone"):
                        phone_input = (
                            ui.input(
                                value=existing_order.phone if existing_order else "",
                                validation=validate_phone,
                            )
                            .props("outlined debounce=2000")
                            .classes("w-full")
                        )

                ui.separator()
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("Line Items").classes("text-lg font-semibold")
                    total_label = ui.label().classes("text-lg font-semibold")

                def draft_total_cents() -> int:
                    total = 0
                    for line in line_drafts:
                        try:
                            price = parse_price_cents(line.unit_price)
                        except ValueError:
                            continue
                        total += max(1, line.quantity) * price
                    return total

                def update_total() -> None:
                    total_label.text = f"Total: {display_price(draft_total_cents())}"

                def add_favorite_item(item_id: int) -> None:
                    item = catalog_by_id[item_id]
                    line = next(
                        (
                            draft
                            for draft in line_drafts
                            if draft.catalog_item_id is None
                            and not draft.description.strip()
                            and not draft.unit_price.strip()
                            and not draft.notes.strip()
                        ),
                        None,
                    )
                    if line is None:
                        line = LineDraft()
                        line_drafts.append(line)
                    line.catalog_item_id = item_id
                    line.description = item.name
                    price_cents = overrides.get(item_id, item.base_price_cents)
                    line.unit_price = f"{price_cents / 100:.2f}"
                    line_editor.refresh()
                    update_total()

                if favorite_items:
                    with (
                        group_box("Quick Add"),
                        ui.element("div").classes("classic-quick-add-grid w-full"),
                    ):
                        for favorite_item in favorite_items:
                            favorite_id = favorite_item.id
                            if favorite_id is None:
                                continue
                            favorite_price = overrides.get(
                                favorite_id, favorite_item.base_price_cents
                            )
                            description = favorite_item.description or "No description"

                            def add_selected_favorite(
                                selected_id: int = favorite_id,
                            ) -> None:
                                add_favorite_item(selected_id)

                            button_text = f"{favorite_item.name} — {display_price(favorite_price)}"
                            alt_text = f"{description} · Cost: {display_price(favorite_price)}"
                            favorite_button = (
                                ui.button(button_text, on_click=add_selected_favorite)
                                .props("flat no-caps align=left")
                                .classes("classic-quick-add-button w-full")
                            )
                            favorite_button.props["aria-label"] = alt_text
                            favorite_button.tooltip(alt_text)

                @ui.refreshable
                def line_editor() -> None:
                    def render_line(index: int, line: LineDraft) -> None:
                        def choose_catalog_item(item_id: int | None) -> None:
                            line.catalog_item_id = item_id
                            if item_id is not None:
                                item = catalog_by_id[item_id]
                                line.description = item.name
                                cents = overrides.get(item_id, item.base_price_cents)
                                line.unit_price = f"{cents / 100:.2f}"
                            line_editor.refresh()
                            update_total()

                        with ui.card().classes("w-full bg-gray-50"):
                            with ui.row().classes("w-full items-end gap-2 flex-wrap"):
                                ui.label(f"#{index}").classes("font-medium w-8 pb-2")
                                with labeled_field("Item / description", classes="grow min-w-56"):
                                    catalog_input = (
                                        ui.input(
                                            value=line.description,
                                            placeholder="Type to search or enter a custom item",
                                        )
                                        .props("outlined dense autocomplete=off")
                                        .classes("w-full")
                                    )

                                def catalog_option_label(item_id: int, name: str) -> str:
                                    item = catalog_by_id[item_id]
                                    price = overrides.get(item_id, item.base_price_cents)
                                    return f"{name} · {display_price(price)}"

                                full_options = {
                                    item_id: catalog_option_label(item_id, name)
                                    for item_id, name in catalog_options.items()
                                    if item_id
                                }

                                def select_from_full_catalog() -> None:
                                    selected = (
                                        int(full_select.value)
                                        if full_select.value is not None
                                        else None
                                    )
                                    full_catalog_dialog.close()
                                    choose_catalog_item(selected)

                                with classic_dialog(
                                    "Select Catalog Item",
                                    accept_label="Select",
                                    on_accept=select_from_full_catalog,
                                    width="560px",
                                ) as full_catalog_dialog:
                                    with group_box("Catalog"), labeled_field("Catalog item"):
                                        full_select = (
                                            ui.select(
                                                full_options,
                                                value=line.catalog_item_id,
                                                with_input=True,
                                            )
                                            .props("outlined options-dense")
                                            .classes("w-full")
                                        )
                                    full_catalog_dialog.set_initial_focus(full_select)

                                ui.button(
                                    icon="expand_circle_down",
                                    on_click=full_catalog_dialog.open,
                                ).props("flat round dense").tooltip("Browse full catalog")

                                with labeled_field("Quantity", classes="w-24"):
                                    quantity_input = (
                                        ui.number(
                                            value=line.quantity,
                                            min=1,
                                            step=1,
                                        )
                                        .props("outlined dense")
                                        .classes("w-full")
                                    )
                                with labeled_field("Unit price", classes="w-36"):
                                    price_input = (
                                        ui.input(value=line.unit_price)
                                        .props("outlined dense prefix=$ inputmode=decimal")
                                        .classes("w-full")
                                    )

                                if not line.notes and not line.show_notes:

                                    def show_notes() -> None:
                                        line.show_notes = True
                                        line_editor.refresh()

                                    ui.button(icon="edit_note", on_click=show_notes).props(
                                        "flat round dense"
                                    ).tooltip("Add notes")

                                def remove_line() -> None:
                                    line_drafts.remove(line)
                                    if not line_drafts:
                                        line_drafts.append(LineDraft())
                                    line_editor.refresh()
                                    update_total()

                                ui.button(icon="delete", on_click=remove_line).props(
                                    "flat round dense color=negative"
                                ).tooltip("Remove line")

                            @ui.refreshable
                            def catalog_suggestions() -> None:
                                query = line.description.strip().casefold()
                                if not query or line.catalog_item_id is not None:
                                    return
                                matches = [
                                    item
                                    for item_id, item in catalog_by_id.items()
                                    if item_id in full_options
                                    and (
                                        query in item.name.casefold()
                                        or query in (item.description or "").casefold()
                                    )
                                ][:5]
                                if not matches:
                                    return

                                with ui.column().classes(
                                    "w-full max-w-xl gap-0 border rounded bg-white"
                                ):

                                    def render_suggestion(item_id: int) -> None:
                                        item = catalog_by_id[item_id]
                                        price = overrides.get(item_id, item.base_price_cents)
                                        ui.button(
                                            f"{item.name} · {display_price(price)}",
                                            on_click=lambda: choose_catalog_item(item_id),
                                        ).props("flat no-caps align=left").classes("w-full")

                                    for match in matches:
                                        if match.id is not None:
                                            render_suggestion(match.id)

                            catalog_suggestions()

                            notes_input = None
                            if line.notes or line.show_notes:
                                with labeled_field("Notes"):
                                    notes_input = (
                                        ui.input(value=line.notes)
                                        .props("outlined dense")
                                        .classes("w-full")
                                    )

                            def search_catalog(
                                change: events.ValueChangeEventArguments[str | None],
                            ) -> None:
                                line.description = change.value or ""
                                selected = catalog_by_id.get(line.catalog_item_id)
                                if selected is None or line.description != selected.name:
                                    line.catalog_item_id = None
                                catalog_suggestions.refresh()

                            def change_quantity(
                                change: events.ValueChangeEventArguments[float | None],
                            ) -> None:
                                line.quantity = max(1, int(change.value or 1))
                                update_total()

                            def change_price(
                                change: events.ValueChangeEventArguments[str | None],
                            ) -> None:
                                line.unit_price = change.value or ""
                                update_total()

                            catalog_input.on_value_change(search_catalog)
                            quantity_input.on_value_change(change_quantity)
                            price_input.on_value_change(change_price)

                            if notes_input is not None:

                                def change_notes(
                                    change: events.ValueChangeEventArguments[str | None],
                                ) -> None:
                                    line.notes = change.value or ""

                                def collapse_empty_notes() -> None:
                                    if not line.notes:
                                        line.show_notes = False
                                        line_editor.refresh()

                                notes_input.on_value_change(change_notes)
                                notes_input.on("blur", collapse_empty_notes)

                    for index, line in enumerate(line_drafts, start=1):
                        render_line(index, line)

                    def add_line() -> None:
                        line_drafts.append(LineDraft())
                        line_editor.refresh()
                        update_total()

                    ui.button("Add Line Item", icon="add", on_click=add_line).props("flat")

                line_editor()
                update_total()
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

                def collect_line_items() -> tuple[list[OrderLine], list[str]]:
                    lines: list[OrderLine] = []
                    warnings: list[str] = []
                    for draft in line_drafts:
                        if not (
                            draft.catalog_item_id
                            or draft.description.strip()
                            or draft.unit_price.strip()
                            or draft.notes.strip()
                        ):
                            continue
                        description = draft.description.strip()
                        if not description:
                            description = "Custom item"
                            warnings.append("A line item was saved as 'Custom item'.")
                        try:
                            price_cents = parse_price_cents(draft.unit_price)
                        except ValueError as error:
                            price_cents = 0
                            warnings.append(f"{description}: {error} Saved at $0.00.")
                        lines.append(
                            OrderLine(
                                line_number=len(lines) + 1,
                                catalog_item_id=draft.catalog_item_id,
                                description=description,
                                quantity=max(1, draft.quantity),
                                unit_price_cents=price_cents,
                                notes=draft.notes.strip() or None,
                            )
                        )
                    if not lines:
                        warnings.append("Order was saved without line items.")
                    return lines, warnings

                def clear_form() -> None:
                    for field in (name_input, phone_input):
                        field.value = ""
                        field.error = None
                    line_drafts.clear()
                    line_drafts.append(LineDraft())
                    line_editor.refresh()
                    update_total()

                async def handle_submit() -> None:
                    line_items, warnings = collect_line_items()
                    work_request = (
                        "; ".join(
                            f"{line.description} x{line.quantity}"
                            if line.quantity > 1
                            else line.description
                            for line in line_items
                        )
                        or "No line items"
                    )
                    total_cents = sum(line.quantity * line.unit_price_cents for line in line_items)
                    order = Order.model_construct(
                        order_id=(
                            existing_order.order_id if existing_order else next_order_id(event)
                        ),
                        timestamp=(
                            existing_order.timestamp
                            if existing_order
                            else datetime.now().astimezone()
                        ),
                        event=event,
                        name=name_input.value,
                        phone=phone_input.value,
                        work_request=work_request,
                        cost=f"{total_cents / 100:.2f}",
                        line_items=line_items,
                    )

                    label_path = render_label(order)
                    saved_order = order.model_copy(update={"label_filename": label_path.name})
                    if existing_order:
                        update_order(saved_order)
                    else:
                        append_order(saved_order)

                    show_warnings(warnings)
                    status_area.clear()
                    with status_area, ui.row().classes("items-center gap-2"):
                        verb = "Updated" if existing_order else "Saved"
                        ui.label(f"{verb} order #{saved_order.order_id}").classes("text-positive")
                        ui.button(
                            icon="article",
                            on_click=lambda path=label_path: open_local_path(path),
                        ).props("flat round dense").classes("text-primary").tooltip(str(label_path))
                        ui.button(
                            icon="print",
                            on_click=lambda path=label_path: print_label_image(path),
                        ).props("flat round dense").classes("text-primary").tooltip(
                            f"Print on {PRINTER_NAME}"
                        )
                    ui.notify(
                        f"{'Updated' if existing_order else 'Saved'} order #{saved_order.order_id}",
                        type="positive",
                    )
                    await print_label_image(label_path)
                    if not existing_order:
                        clear_form()
                        order_title.text = f"Order #{next_order_id(event)}"

                submit_text = "Save Changes" if existing_order else "Submit Order"
                with ui.row().classes("w-full justify-end"):
                    ui.button(submit_text, on_click=handle_submit).props("color=primary size=lg")

            status_detail = (
                f"Editing order #{existing_order.order_id}" if existing_order else "New order"
            )
            application_status("Ready", status_detail)

    @ui.page("/events/{folder_name}")
    def intake_page(folder_name: str) -> None:
        render_intake_page(folder_name)

    @ui.page("/events/{folder_name}/orders/{order_id}/edit")
    def edit_order_page(folder_name: str, order_id: int) -> None:
        render_intake_page(folder_name, order_id)
