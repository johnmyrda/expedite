"""Event details and catalog price override management."""

from nicegui import events, ui
from nicegui.elements.input import Input

from expedite.models import Event
from expedite.money import display_price, parse_price_cents
from expedite.pages.components import (
    application_menu,
    application_status,
    group_box,
    labeled_field,
    sortable_header,
    update_application_status,
)
from expedite.pages.navigation import event_navigation_tabs
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
            with ui.column().classes("app-page w-full p-6 gap-4"):
                application_menu()
                ui.label("Event not found").classes("text-2xl font-bold text-negative")
                ui.button("Back to Events", on_click=lambda: ui.navigate.to("/"))
                application_status("Event not found")
            return

        event: Event = loaded_event
        ui.page_title(f"{event.name} - Manage")
        filters: dict[str, str | bool] = {
            "query": "",
            "pricing": "all",
            "sort_key": "name",
            "sort_descending": False,
        }

        with ui.column().classes("app-page w-full p-6 gap-6"):
            application_menu()
            with ui.row().classes("app-page-header w-full items-center justify-between"):
                title = ui.label(f"Manage {event.name}").classes(
                    "app-page-title text-3xl font-bold"
                )

            event_navigation_tabs(folder_name, "management")

            with group_box("Event Details"), ui.row().classes("w-full items-end gap-3 flex-wrap"):
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
                    title.text = f"Manage {event.name}"
                    ui.page_title(f"{event.name} - Manage")
                    update_application_status("Event details saved", event.name)

                ui.button("Save Details", on_click=save_details).props("color=primary")

            with group_box("Catalog Price Overrides"):
                ui.label(
                    "Prices save automatically when you press Enter or leave the field. "
                    "Leave an event price blank to use the catalog base price."
                ).classes("text-sm text-gray-500")
                with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                    with labeled_field("Filter by name or description", classes="grow min-w-64"):
                        filter_input = ui.input().props("outlined clearable").classes("w-full")
                    pricing_filter = (
                        ui.toggle(
                            {
                                "all": "All",
                                "overridden": "Overridden",
                                "base": "Using Base",
                            },
                            value="all",
                        )
                        .props("no-caps")
                        .classes("pricing-filter")
                    )

                @ui.refreshable
                def price_list() -> None:
                    query = str(filters["query"]).strip().casefold()
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

                    sort_key = str(filters["sort_key"])
                    key_functions = {
                        "name": lambda item: item.name.casefold(),
                        "base_price": lambda item: item.base_price_cents,
                        "event_price": lambda item: overrides.get(item.id, item.base_price_cents),
                    }
                    items.sort(
                        key=key_functions[sort_key],
                        reverse=bool(filters["sort_descending"]),
                    )

                    def change_sort(column_key: str) -> None:
                        if filters["sort_key"] == column_key:
                            filters["sort_descending"] = not bool(filters["sort_descending"])
                        else:
                            filters["sort_key"] = column_key
                            filters["sort_descending"] = False
                        price_list.refresh()

                    ui.label(f"{len(items)} item(s)").classes("text-sm text-gray-500")
                    with (
                        ui.element("div").classes("classic-list-panel"),
                        ui.element("table").classes("classic-list management-price-list"),
                    ):
                        with ui.element("thead"), ui.element("tr"):
                            for heading, column_key, width in (
                                ("Item", "name", "auto"),
                                ("Base Price", "base_price", "130px"),
                                ("Event Price", "event_price", "180px"),
                                ("Actions", None, "64px"),
                            ):
                                with ui.element("th").style(f"width: {width}"):
                                    if column_key is None:
                                        ui.label(heading)
                                    else:
                                        sortable_header(
                                            heading,
                                            active=filters["sort_key"] == column_key,
                                            descending=bool(filters["sort_descending"]),
                                            on_click=lambda key=column_key: change_sort(key),
                                        )
                        with ui.element("tbody"):
                            if not items:
                                with (
                                    ui.element("tr"),
                                    ui.element("td").props("colspan=4"),
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
                                        ui.label(item.name).classes("font-medium")
                                        if item.description:
                                            ui.label(item.description).classes(
                                                "management-item-description"
                                            )
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
                                    with ui.element("td").classes("classic-actions"):
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
                                                    parse_price_cents(raw_value)
                                                    if raw_value
                                                    else None
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
                                            update_application_status(message, item_name)

                                        price_input.on("blur", save_override)
                                        price_input.on(
                                            "keydown",
                                            js_handler=(
                                                "(event) => { if (event.key === 'Enter') {"
                                                " event.preventDefault(); event.target.blur(); } }"
                                            ),
                                        )

                                        if override is not None:

                                            def clear_override(
                                                catalog_item_id: int | None = item.id,
                                                item_name: str = item.name,
                                            ) -> None:
                                                if catalog_item_id is None:
                                                    return
                                                save_event_catalog_price(
                                                    event, catalog_item_id, None
                                                )
                                                price_list.refresh()
                                                update_application_status(
                                                    "Override cleared", item_name
                                                )

                                            reset_button = ui.button(
                                                icon="restart_alt", on_click=clear_override
                                            ).props("flat round dense")
                                            reset_button.props["aria-label"] = (
                                                f"Use base price for {item.name}"
                                            )
                                            reset_button.tooltip("Use catalog base price")

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

            application_status("Ready", event.name)
