"""Event details and catalog price override management."""

from dataclasses import dataclass
from typing import Literal

from nicegui import events, ui
from nicegui.elements.button import Button
from nicegui.elements.input import Input

from expedite.models import Event
from expedite.money import display_price, parse_price_cents
from expedite.pages.application_shell import (
    ApplicationStatus,
    application_menu,
    application_status,
)
from expedite.pages.catalog_ui import (
    catalog_item_matches,
    compact_catalog_item,
    effective_event_price_cents,
)
from expedite.pages.classic_ui import group_box, labeled_field, sortable_header
from expedite.pages.navigation import (
    event_navigation_tabs,
    event_not_found_page,
    event_page_header,
)
from expedite.storage.events import get_event
from expedite.storage.sqlite_store import (
    event_catalog_prices,
    list_catalog_items,
    save_event,
    save_event_catalog_price,
)

PricingFilter = Literal["all", "overridden", "base"]
PriceSortKey = Literal["name", "base_price", "event_price"]


@dataclass
class PriceListState:
    """Mutable filtering and sorting state for event catalog prices."""

    query: str = ""
    pricing: PricingFilter = "all"
    sort_key: PriceSortKey = "name"
    sort_descending: bool = False


def register_event_details_page() -> None:
    @ui.page("/events/{folder_name}/manage")
    def event_details_page(folder_name: str) -> None:
        loaded_event = get_event(folder_name)
        if loaded_event is None:
            event_not_found_page()
            return

        event: Event = loaded_event
        ui.page_title(f"{event.name} - Manage")
        state = PriceListState()
        status = ApplicationStatus(detail=event.name)

        with ui.column().classes("app-page event-details-page w-full p-6 gap-6"):
            application_menu(status)
            title = event_page_header(event)
            event_navigation_tabs(folder_name, "management")
            panel = ui.column().classes("event-page-content w-full gap-4")

            with panel, ui.row().classes(
                "event-details-editor w-full items-end gap-3 flex-wrap"
            ):
                with labeled_field("Event name", classes="grow min-w-64"):
                    name_input = ui.input(value=event.name).props("outlined").classes("w-full")
                with labeled_field("Start date", classes="w-48"):
                    date_input = (
                        ui.input(value=event.start_date)
                        .props("outlined type=date")
                        .classes("w-full")
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
                    title.text = event.name
                    ui.page_title(f"{event.name} - Manage")
                    status.update("Event details saved", event.name)

                ui.button("Save Details", on_click=save_details).props("color=primary")

            with panel, group_box("Catalog Price Overrides"):
                ui.label(
                    "Prices save when pressing Enter or leaving the field. "
                    "Leave price blank to use base price."
                ).classes("text-sm text-gray-500")
                with ui.row().classes("w-full items-end gap-3 flex-wrap"):
                    with labeled_field("Filter by name or description", classes="grow min-w-64"):
                        filter_input = ui.input().props("outlined clearable").classes("w-full")
                    with ui.row().classes("pricing-filter-controls items-center gap-1"):
                        ui.element("div").classes("classic-toolbar-separator")
                        with ui.row().classes("pricing-filter items-center gap-0").props(
                            'role=group aria-label="Price filter"'
                        ):
                            pricing_buttons: dict[PricingFilter, Button] = {}

                            def choose_filter(selected: PricingFilter) -> None:
                                state.pricing = selected
                                for key, button in pricing_buttons.items():
                                    button.props["aria-pressed"] = str(key == selected).lower()
                                price_list.refresh()

                            choices: tuple[tuple[PricingFilter, str, str], ...] = (
                                ("all", "view_list", "Show all catalog items"),
                                (
                                    "overridden",
                                    "edit",
                                    "Show items with an event price override",
                                ),
                                ("base", "sell", "Show items using the catalog base price"),
                            )
                            for choice, icon, description in choices:
                                button = ui.button(
                                    icon=icon, on_click=lambda key=choice: choose_filter(key)
                                ).props("flat dense")
                                button.props["aria-label"] = description
                                button.props["aria-pressed"] = str(choice == state.pricing).lower()
                                button.tooltip(description)
                                pricing_buttons[choice] = button

                @ui.refreshable
                def price_list() -> None:
                    overrides = event_catalog_prices(event)
                    items = []
                    for item in list_catalog_items():
                        matches_text = catalog_item_matches(item, state.query)
                        has_override = item.id in overrides
                        matches_pricing = (
                            state.pricing == "all"
                            or (state.pricing == "overridden" and has_override)
                            or (state.pricing == "base" and not has_override)
                        )
                        if matches_text and matches_pricing:
                            items.append(item)

                    sort_key = state.sort_key
                    key_functions = {
                        "name": lambda item: item.name.casefold(),
                        "base_price": lambda item: item.base_price_cents,
                        "event_price": lambda item: effective_event_price_cents(item, overrides),
                    }
                    items.sort(
                        key=key_functions[sort_key],
                        reverse=state.sort_descending,
                    )

                    def change_sort(column_key: PriceSortKey) -> None:
                        if state.sort_key == column_key:
                            state.sort_descending = not state.sort_descending
                        else:
                            state.sort_key = column_key
                            state.sort_descending = False
                        price_list.refresh()

                    ui.label(f"{len(items)} item(s)").classes("text-sm text-gray-500")
                    with (
                        ui.element("div").classes("classic-list-panel page-scroll-list"),
                        ui.element("table").classes("classic-list management-price-list"),
                    ):
                        with ui.element("thead"), ui.element("tr"):
                            for heading, column_key, width in (
                                ("Item", "name", "auto"),
                                ("Base Price", "base_price", "130px"),
                                ("Event Price", "event_price", "180px"),
                            ):
                                with ui.element("th").style(f"width: {width}"):
                                    sortable_header(
                                        heading,
                                        active=state.sort_key == column_key,
                                        descending=state.sort_descending,
                                        on_click=lambda key=column_key: change_sort(key),
                                    )
                        with ui.element("tbody"):
                            if not items:
                                with (
                                    ui.element("tr"),
                                    ui.element("td").props("colspan=3"),
                                ):
                                    ui.label("No catalog items match this filter.")

                            for item in items:
                                override = overrides.get(item.id) if item.id is not None else None
                                row = ui.element("tr").classes(
                                    "management-price-row"
                                    + (" has-override" if override is not None else "")
                                    + (" is-inactive" if not item.active else "")
                                )
                                if not item.active and override is not None:
                                    row.props(
                                        'title="Inactive catalog item with an event price override"'
                                    )
                                elif not item.active:
                                    row.props('title="Inactive catalog item"')
                                elif override is not None:
                                    row.props('title="Event price override"')
                                with row:
                                    with ui.element("td"):
                                        compact_catalog_item(item)
                                    with ui.element("td"):
                                        ui.label(display_price(item.base_price_cents))
                                    with ui.element("td"):
                                        price_input = (
                                            ui.input(
                                                value=(
                                                    f"{override / 100:.2f}"
                                                    if override is not None
                                                    else ""
                                                ),
                                            )
                                            .props("outlined dense prefix=$ inputmode=decimal")
                                            .classes("management-price-input w-full")
                                        )
                                        price_input.props["aria-label"] = (
                                            f"Event price for {item.name}"
                                        )
                                    last_saved_price = {"value": override}

                                    def save_override(
                                        catalog_item_id: int | None = item.id,
                                        price_field: Input = price_input,
                                        item_name: str = item.name,
                                        saved_price: dict[str, int | None] = last_saved_price,
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
                                        if price_cents == saved_price["value"]:
                                            return
                                        save_event_catalog_price(
                                            event, catalog_item_id, price_cents
                                        )
                                        saved_price["value"] = price_cents
                                        message = (
                                            "Override saved"
                                            if price_cents is not None
                                            else "Override cleared"
                                        )
                                        price_list.refresh()
                                        status.update(message, item_name)

                                    price_input.on("blur", save_override)
                                    price_input.on("keydown.enter.prevent", save_override)

                def handle_filter_change(
                    change: events.ValueChangeEventArguments[str | None],
                ) -> None:
                    state.query = change.value or ""
                    price_list.refresh()

                filter_input.on_value_change(handle_filter_change)
                price_list()

            application_status(status)
