"""Catalog management page."""

from nicegui import events, ui

from expedite.config import APP_NAME
from expedite.models import CatalogItem
from expedite.money import display_price, parse_price_cents
from expedite.pages.components import (
    application_menu,
    application_status,
    group_box,
    labeled_field,
)
from expedite.storage.sqlite_store import (
    MAX_CATALOG_FAVORITES,
    list_catalog_favorite_ids,
    list_catalog_items,
    save_catalog_item,
    set_catalog_item_favorite,
)
from expedite.theme import apply_windows_98_theme


def register_catalog_page() -> None:
    @ui.page("/catalog")
    def catalog_page() -> None:
        apply_windows_98_theme()
        ui.page_title(f"{APP_NAME} - Catalog")

        state: dict[str, int | str | bool | None] = {
            "filter": "",
            "editing_id": None,
            "creating": False,
        }

        with ui.column().classes("app-page w-full p-6 gap-6"):
            application_menu()
            with ui.row().classes("app-page-header w-full items-center justify-between"):
                ui.label("Catalog").classes("app-page-title text-3xl font-bold")

            with group_box("Catalog Items"):
                with ui.row().classes("w-full items-end gap-3"):
                    with labeled_field("Filter by name or description", classes="grow"):
                        filter_input = ui.input().props("outlined clearable").classes("w-full")

                    def start_create() -> None:
                        state["editing_id"] = None
                        state["creating"] = True
                        item_list.refresh()

                    ui.button("New Item...", on_click=start_create).props("color=primary")

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
                    favorite_ids = set(list_catalog_favorite_ids())

                    ui.label(
                        f"{len(items)} item(s) · "
                        f"{len(favorite_ids)}/{MAX_CATALOG_FAVORITES} favorites"
                    ).classes("text-sm text-gray-500")

                    def toggle_favorite(item: CatalogItem, favorite: bool) -> None:
                        if item.id is None:
                            return
                        try:
                            set_catalog_item_favorite(item.id, favorite)
                        except ValueError as error:
                            ui.notify(str(error), type="negative")
                        else:
                            action = "Added to" if favorite else "Removed from"
                            selected_count = len(list_catalog_favorite_ids())
                            ui.notify(
                                f"{action} intake favorites: {item.name} "
                                f"({selected_count}/{MAX_CATALOG_FAVORITES} selected)",
                                type="positive",
                            )
                            item_list.refresh()

                    def cancel_edit() -> None:
                        state["editing_id"] = None
                        state["creating"] = False
                        item_list.refresh()

                    def render_editor(item: CatalogItem | None) -> None:
                        title = "Edit Catalog Item" if item else "New Catalog Item"
                        with group_box(title):
                            with ui.row().classes("w-full items-end gap-3 flex-wrap"):
                                with labeled_field("Name", classes="grow min-w-64"):
                                    name_input = (
                                        ui.input(value=item.name if item else "")
                                        .props("outlined dense")
                                        .classes("w-full")
                                    )
                                with labeled_field("Base price", classes="w-40"):
                                    price_input = (
                                        ui.input(
                                            value=(
                                                f"{item.base_price_cents / 100:.2f}" if item else ""
                                            )
                                        )
                                        .props("outlined dense prefix=$ inputmode=decimal")
                                        .classes("w-full")
                                    )
                                active_input = ui.checkbox(
                                    "Active", value=item.active if item else True
                                )
                            with labeled_field("Description"):
                                description_input = (
                                    ui.textarea(value=item.description or "" if item else "")
                                    .props("outlined dense autogrow")
                                    .classes("w-full")
                                )

                            def handle_save() -> None:
                                name = (name_input.value or "").strip()
                                if not name:
                                    ui.notify("Name is required.", type="negative")
                                    return
                                try:
                                    price_cents = parse_price_cents(price_input.value)
                                except ValueError as error:
                                    ui.notify(str(error), type="negative")
                                    return

                                saved = save_catalog_item(
                                    item_id=item.id if item else None,
                                    name=name,
                                    description=(description_input.value or "").strip() or None,
                                    base_price_cents=price_cents,
                                    active=bool(active_input.value),
                                )
                                ui.notify(f"Saved {saved.name}", type="positive")
                                state["editing_id"] = None
                                state["creating"] = False
                                item_list.refresh()

                            with ui.row().classes("w-full justify-end gap-2"):
                                ui.button("Save", on_click=handle_save).props("color=primary")
                                ui.button("Cancel", on_click=cancel_edit).props("flat")

                    if state["creating"]:
                        render_editor(None)

                    with ui.element("div").classes("classic-list-panel"):
                        with ui.element("table").classes("classic-list"):
                            with ui.element("thead"):
                                with ui.element("tr"):
                                    for heading, width in (
                                        ("Favorite", "86px"),
                                        ("Name", "22%"),
                                        ("Description", "auto"),
                                        ("Price", "110px"),
                                        ("Status", "90px"),
                                        ("Actions", "80px"),
                                    ):
                                        with ui.element("th").style(f"width: {width}"):
                                            ui.label(heading)
                            with ui.element("tbody"):
                                if not items and not state["creating"]:
                                    with ui.element("tr"):
                                        with ui.element("td").props("colspan=6"):
                                            ui.label("No catalog items match this filter.")

                                for item in items:
                                    if state["editing_id"] == item.id:
                                        with ui.element("tr"):
                                            with ui.element("td").props("colspan=6"):
                                                render_editor(item)
                                        continue

                                    with ui.element("tr"):
                                        is_favorite = item.id in favorite_ids
                                        with ui.element("td").classes("classic-actions"):

                                            def handle_favorite(
                                                selected: CatalogItem = item,
                                                favorite: bool = not is_favorite,
                                            ) -> None:
                                                toggle_favorite(selected, favorite)

                                            favorite_button = ui.button(
                                                icon="star" if is_favorite else "star_border",
                                                on_click=handle_favorite,
                                            ).props("flat round dense color=amber-8")
                                            favorite_button.tooltip(
                                                "Remove from intake favorites"
                                                if is_favorite
                                                else "Show as an intake favorite"
                                            )
                                            if not item.active:
                                                favorite_button.disable()
                                        with ui.element("td"):
                                            ui.label(item.name).classes("font-medium")
                                        with ui.element("td"):
                                            ui.label(item.description or "")
                                        with ui.element("td"):
                                            ui.label(display_price(item.base_price_cents))
                                        with ui.element("td"):
                                            ui.label("Active" if item.active else "Inactive")
                                        with ui.element("td").classes("classic-actions"):

                                            def start_edit(selected: CatalogItem = item) -> None:
                                                state["creating"] = False
                                                state["editing_id"] = selected.id
                                                item_list.refresh()

                                            ui.button("Edit...", on_click=start_edit).props(
                                                "flat dense"
                                            )

                def handle_filter_change(
                    event: events.ValueChangeEventArguments[str | None],
                ) -> None:
                    state["filter"] = event.value or ""
                    item_list.refresh()

                filter_input.on_value_change(handle_filter_change)
                item_list()

            application_status("Ready", "Catalog")
