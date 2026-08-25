"""Catalog management page."""

from decimal import Decimal, InvalidOperation

from nicegui import events, ui

from expedite.config import APP_NAME
from expedite.models import CatalogItem
from expedite.storage.sqlite_store import list_catalog_items, save_catalog_item


def _parse_price_cents(value: str | None) -> int:
    normalized = (value or "").strip().replace("$", "").replace(",", "")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as error:
        raise ValueError("Enter a valid price.") from error
    if not amount.is_finite() or amount < 0:
        raise ValueError("Price must be zero or greater.")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("Price cannot have more than two decimal places.")
    return int(amount * 100)


def _display_price(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def register_catalog_page() -> None:
    @ui.page("/catalog")
    def catalog_page() -> None:
        ui.page_title(f"{APP_NAME} - Catalog")
        ui.add_head_html("<style>body { background: #f7f7f7; }</style>")

        state: dict[str, int | str | bool | None] = {
            "filter": "",
            "editing_id": None,
            "creating": False,
        }

        with ui.column().classes("w-full max-w-6xl mx-auto p-6 gap-6"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Catalog").classes("text-3xl font-bold")
                ui.button("Events", on_click=lambda: ui.navigate.to("/")).props("flat")

            with ui.row().classes("w-full items-center gap-3"):
                filter_input = (
                    ui.input("Filter by name or description")
                    .props("outlined clearable prepend-icon=search")
                    .classes("grow")
                )

                def start_create() -> None:
                    state["editing_id"] = None
                    state["creating"] = True
                    item_list.refresh()

                ui.button("New Item", icon="add", on_click=start_create).props(
                    "color=primary"
                )

            @ui.refreshable
            def item_list() -> None:
                query = str(state["filter"] or "").strip().casefold()
                items = [
                    item
                    for item in list_catalog_items()
                    if not query
                    or query in item.name.casefold()
                    or query in (item.description or "").casefold()
                ]

                ui.label(f"{len(items)} item(s)").classes("text-sm text-gray-500")

                def cancel_edit() -> None:
                    state["editing_id"] = None
                    state["creating"] = False
                    item_list.refresh()

                def render_editor(item: CatalogItem | None) -> None:
                    with ui.column().classes("w-full gap-3 px-4 py-4 bg-blue-50"):
                        with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                            name_input = (
                                ui.input("Name", value=item.name if item else "")
                                .props("outlined dense")
                                .classes("grow min-w-64")
                            )
                            price_input = (
                                ui.input(
                                    "Base price",
                                    value=(
                                        f"{item.base_price_cents / 100:.2f}"
                                        if item
                                        else ""
                                    ),
                                )
                                .props("outlined dense prefix=$ inputmode=decimal")
                                .classes("w-40")
                            )
                            active_input = ui.checkbox(
                                "Active", value=item.active if item else True
                            )
                        description_input = (
                            ui.textarea(
                                "Description",
                                value=item.description or "" if item else "",
                            )
                            .props("outlined dense autogrow")
                            .classes("w-full")
                        )

                        def handle_save() -> None:
                            name = (name_input.value or "").strip()
                            if not name:
                                ui.notify("Name is required.", type="negative")
                                return
                            try:
                                price_cents = _parse_price_cents(price_input.value)
                            except ValueError as error:
                                ui.notify(str(error), type="negative")
                                return

                            saved = save_catalog_item(
                                item_id=item.id if item else None,
                                name=name,
                                description=(description_input.value or "").strip()
                                or None,
                                base_price_cents=price_cents,
                                active=bool(active_input.value),
                            )
                            ui.notify(f"Saved {saved.name}", type="positive")
                            state["editing_id"] = None
                            state["creating"] = False
                            item_list.refresh()

                        with ui.row().classes("gap-2"):
                            ui.button("Save", on_click=handle_save).props("color=primary")
                            ui.button("Cancel", on_click=cancel_edit).props("flat")

                with ui.card().classes("w-full p-0 gap-0"):
                    if state["creating"]:
                        render_editor(None)

                    if not items and not state["creating"]:
                        ui.label("No catalog items match this filter.").classes(
                            "text-gray-500 px-4 py-6"
                        )

                    for item in items:
                        if state["editing_id"] == item.id:
                            render_editor(item)
                            continue

                        with ui.row().classes(
                            "w-full items-center gap-4 px-4 py-3 border-b"
                        ):
                            with ui.column().classes("grow min-w-0 gap-0"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.label(item.name).classes("font-medium")
                                    if not item.active:
                                        ui.badge("Inactive", color="grey")
                                if item.description:
                                    ui.label(item.description).classes(
                                        "text-sm text-gray-500"
                                    )
                            ui.label(_display_price(item.base_price_cents)).classes(
                                "font-medium whitespace-nowrap"
                            )

                            def start_edit(selected: CatalogItem = item) -> None:
                                state["creating"] = False
                                state["editing_id"] = selected.id
                                item_list.refresh()

                            ui.button(icon="edit", on_click=start_edit).props(
                                "flat round dense"
                            ).tooltip("Edit item")

            def handle_filter_change(
                event: events.ValueChangeEventArguments[str | None],
            ) -> None:
                state["filter"] = event.value or ""
                item_list.refresh()

            filter_input.on_value_change(handle_filter_change)
            item_list()
