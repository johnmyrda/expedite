"""Event details and catalog price override management."""

from nicegui import events, ui
from nicegui.elements.input import Input

from expedite.models import Event
from expedite.money import display_price, parse_price_cents
from expedite.storage.events import get_event
from expedite.storage.sqlite_store import (
    event_catalog_prices,
    list_catalog_items,
    save_event,
    save_event_catalog_price,
)
from expedite.theme import apply_windows_98_theme


def register_event_details_page() -> None:
    @ui.page("/events/{folder_name}/manage")
    def event_details_page(folder_name: str) -> None:
        apply_windows_98_theme()
        loaded_event = get_event(folder_name)
        if loaded_event is None:
            with ui.column().classes("win98-window w-full max-w-2xl mx-auto p-6 gap-4"):
                ui.label("Event not found").classes("text-2xl font-bold text-negative")
                ui.button("Back to Events", on_click=lambda: ui.navigate.to("/"))
            return

        event: Event = loaded_event
        ui.page_title(f"{event.name} - Manage")
        filters = {"query": "", "pricing": "all"}

        with ui.column().classes("win98-window w-full max-w-6xl mx-auto p-6 gap-6"):
            with ui.row().classes("win98-title-bar w-full items-center justify-between"):
                title = ui.label(f"Manage {event.name}").classes(
                    "win98-title-bar-text text-3xl font-bold"
                )
                with ui.row().classes("gap-2"):
                    ui.button(
                        "Intake",
                        on_click=lambda: ui.navigate.to(f"/events/{folder_name}"),
                    ).props("flat")
                    ui.button(
                        "Orders",
                        on_click=lambda: ui.navigate.to(f"/events/{folder_name}/orders"),
                    ).props("flat")
                    ui.button("Events", on_click=lambda: ui.navigate.to("/")).props("flat")

            with ui.card().classes("w-full"):
                ui.label("Event Details").classes("text-xl font-semibold")
                with ui.row().classes("w-full items-end gap-3 flex-wrap"):
                    name_input = (
                        ui.input("Event name", value=event.name)
                        .props("outlined")
                        .classes("grow min-w-64")
                    )
                    date_input = (
                        ui.input("Start date", value=event.start_date)
                        .props("outlined type=date")
                        .classes("w-48")
                    )

                    def save_details() -> None:
                        nonlocal event
                        name = (name_input.value or "").strip()
                        start_date = (date_input.value or "").strip()
                        if not name or not start_date:
                            ui.notify("Event name and start date are required.", type="negative")
                            return
                        event = event.model_copy(update={"name": name, "start_date": start_date})
                        save_event(event)
                        title.text = f"Manage {event.name}"
                        ui.page_title(f"{event.name} - Manage")
                        ui.notify("Event details saved", type="positive")

                    ui.button("Save Details", on_click=save_details).props("color=primary")

            with ui.card().classes("w-full"):
                ui.label("Catalog Price Overrides").classes("text-xl font-semibold")
                ui.label("Leave an event price blank to use the catalog base price.").classes(
                    "text-sm text-gray-500"
                )
                with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                    filter_input = (
                        ui.input("Filter by name or description")
                        .props("outlined clearable prepend-icon=search")
                        .classes("grow min-w-64")
                    )
                    pricing_filter = ui.toggle(
                        {
                            "all": "All",
                            "overridden": "Overridden",
                            "base": "Using Base",
                        },
                        value="all",
                    ).props("no-caps")

                @ui.refreshable
                def price_list() -> None:
                    query = filters["query"].strip().casefold()
                    overrides = event_catalog_prices(event)
                    items = []
                    for item in list_catalog_items():
                        matches_text = (
                            not query
                            or query in item.name.casefold()
                            or query in (item.description or "").casefold()
                        )
                        has_override = item.id in overrides
                        matches_pricing = (
                            filters["pricing"] == "all"
                            or (filters["pricing"] == "overridden" and has_override)
                            or (filters["pricing"] == "base" and not has_override)
                        )
                        if matches_text and matches_pricing:
                            items.append(item)

                    ui.label(f"{len(items)} item(s)").classes("text-sm text-gray-500")
                    if not items:
                        ui.label("No catalog items match this filter.").classes(
                            "text-gray-500 py-4"
                        )
                        return

                    with ui.column().classes("w-full gap-0 border rounded"):
                        for item in items:
                            override = overrides.get(item.id) if item.id is not None else None
                            with ui.row().classes(
                                "w-full items-center gap-3 px-3 py-2 border-b flex-wrap"
                            ):
                                with ui.column().classes("grow min-w-64 gap-0"):
                                    with ui.row().classes("items-center gap-2"):
                                        ui.label(item.name).classes("font-medium")
                                        if not item.active:
                                            ui.badge("Inactive", color="grey")
                                    if item.description:
                                        ui.label(item.description).classes("text-sm text-gray-500")
                                ui.label(f"Base: {display_price(item.base_price_cents)}").classes(
                                    "w-32 text-sm text-gray-600"
                                )
                                price_input = (
                                    ui.input(
                                        "Event price",
                                        value=(
                                            f"{override / 100:.2f}" if override is not None else ""
                                        ),
                                    )
                                    .props("outlined dense prefix=$ inputmode=decimal")
                                    .classes("w-40")
                                )

                                def save_override(
                                    catalog_item_id: int | None = item.id,
                                    price_field: Input = price_input,
                                ) -> None:
                                    if catalog_item_id is None:
                                        return
                                    raw_value = (price_field.value or "").strip()
                                    try:
                                        price_cents = (
                                            parse_price_cents(raw_value) if raw_value else None
                                        )
                                    except ValueError as error:
                                        ui.notify(str(error), type="negative")
                                        return
                                    save_event_catalog_price(event, catalog_item_id, price_cents)
                                    message = (
                                        "Override saved"
                                        if price_cents is not None
                                        else "Override cleared"
                                    )
                                    ui.notify(message, type="positive")
                                    price_list.refresh()

                                ui.button(icon="save", on_click=save_override).props(
                                    "flat round dense color=primary"
                                ).tooltip("Save event price")

                                if override is not None:

                                    def clear_override(
                                        catalog_item_id: int | None = item.id,
                                    ) -> None:
                                        if catalog_item_id is None:
                                            return
                                        save_event_catalog_price(event, catalog_item_id, None)
                                        ui.notify("Override cleared", type="positive")
                                        price_list.refresh()

                                    ui.button(icon="restart_alt", on_click=clear_override).props(
                                        "flat round dense"
                                    ).tooltip("Use catalog base price")

                def handle_filter_change(
                    change: events.ValueChangeEventArguments[str | None],
                ) -> None:
                    filters["query"] = change.value or ""
                    price_list.refresh()

                def handle_pricing_filter_change(
                    change: events.ValueChangeEventArguments[str | None],
                ) -> None:
                    filters["pricing"] = change.value or "all"
                    price_list.refresh()

                filter_input.on_value_change(handle_filter_change)
                pricing_filter.on_value_change(handle_pricing_filter_change)
                price_list()
