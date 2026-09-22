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
            "selected_id": None,
            "editing_id": None,
            "creating": False,
        }

        def visible_items() -> list[CatalogItem]:
            query = str(state["filter"] or "").strip().casefold()
            return [
                item
                for item in list_catalog_items()
                if not query
                or query in item.name.casefold()
                or query in (item.description or "").casefold()
            ]

        def selected_item() -> CatalogItem | None:
            selected_id = state["selected_id"]
            return next(
                (item for item in list_catalog_items() if item.id == selected_id),
                None,
            )

        @ui.refreshable
        def catalog_status() -> None:
            item = selected_item()
            favorite_count = len(list_catalog_favorite_ids())
            detail = (
                f"{item.name} selected · {favorite_count}/{MAX_CATALOG_FAVORITES} favorites"
                if item is not None
                else f"{len(visible_items())} item(s) · "
                f"{favorite_count}/{MAX_CATALOG_FAVORITES} favorites"
            )
            application_status("Ready", detail)

        with ui.column().classes("app-page w-full p-6 gap-6"):
            application_menu()
            with ui.row().classes("app-page-header w-full items-center justify-between"):
                ui.label("Catalog").classes("app-page-title text-3xl font-bold")

            with group_box("Catalog Items"):
                with labeled_field("Filter by name or description"):
                    filter_input = ui.input().props("outlined clearable").classes("w-full")

                @ui.refreshable
                def item_list() -> None:
                    items = visible_items()
                    favorite_ids = set(list_catalog_favorite_ids())
                    row_elements = {}

                    def current_item() -> CatalogItem | None:
                        return next(
                            (item for item in items if item.id == state["selected_id"]),
                            None,
                        )

                    def refresh_catalog() -> None:
                        item_list.refresh()
                        catalog_status.refresh()

                    def configure_toolbar() -> None:
                        item = current_item()
                        editing = state["editing_id"] is not None or bool(state["creating"])
                        favorite_button.set_text(
                            "Remove Favorite"
                            if item is not None and item.id in favorite_ids
                            else "Add Favorite"
                        )
                        active_button.set_text(
                            "Deactivate" if item is None or item.active else "Activate"
                        )
                        edit_button.enabled = item is not None and not editing
                        active_button.enabled = item is not None and not editing
                        favorite_available = (
                            item is not None
                            and item.active
                            and not editing
                            and (
                                item.id in favorite_ids or len(favorite_ids) < MAX_CATALOG_FAVORITES
                            )
                        )
                        favorite_button.enabled = favorite_available

                    def select_item(item_id: int | None) -> None:
                        previous_id = state["selected_id"]
                        if previous_id in row_elements:
                            row_elements[previous_id].classes(remove="is-selected")
                        state["selected_id"] = item_id
                        if item_id in row_elements:
                            row_elements[item_id].classes(add="is-selected")
                        configure_toolbar()
                        catalog_status.refresh()

                    def start_create() -> None:
                        state["selected_id"] = None
                        state["editing_id"] = None
                        state["creating"] = True
                        refresh_catalog()

                    def start_edit(item_id: int | None = None) -> None:
                        selected_id = item_id if item_id is not None else state["selected_id"]
                        if selected_id is None:
                            return
                        state["selected_id"] = selected_id
                        state["creating"] = False
                        state["editing_id"] = selected_id
                        refresh_catalog()

                    def toggle_favorite() -> None:
                        item = current_item()
                        if item is None or item.id is None:
                            return
                        favorite = item.id not in favorite_ids
                        try:
                            set_catalog_item_favorite(item.id, favorite)
                        except ValueError as error:
                            ui.notify(str(error), type="negative")
                        else:
                            action = "Added to" if favorite else "Removed from"
                            ui.notify(
                                f"{action} intake favorites: {item.name}",
                                type="positive",
                            )
                            refresh_catalog()

                    def toggle_active() -> None:
                        item = current_item()
                        if item is None:
                            return
                        saved = save_catalog_item(
                            item_id=item.id,
                            name=item.name,
                            description=item.description,
                            base_price_cents=item.base_price_cents,
                            active=not item.active,
                        )
                        action = "Activated" if saved.active else "Deactivated"
                        ui.notify(f"{action} {saved.name}", type="positive")
                        refresh_catalog()

                    with ui.row().classes("classic-list-toolbar w-full items-center gap-1"):
                        ui.button("New...", on_click=start_create).props("flat dense")
                        edit_button = ui.button("Edit...", on_click=lambda: start_edit()).props(
                            "flat dense"
                        )
                        ui.element("div").classes("classic-toolbar-separator")
                        favorite_button = ui.button("Add Favorite", on_click=toggle_favorite).props(
                            "flat dense"
                        )
                        active_button = ui.button("Deactivate", on_click=toggle_active).props(
                            "flat dense"
                        )
                        configure_toolbar()

                    def cancel_edit() -> None:
                        state["editing_id"] = None
                        state["creating"] = False
                        refresh_catalog()

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
                                state["selected_id"] = saved.id
                                state["editing_id"] = None
                                state["creating"] = False
                                refresh_catalog()

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
                                        ("Fav", "60px"),
                                        ("Name", "24%"),
                                        ("Description", "auto"),
                                        ("Price", "120px"),
                                        ("Status", "100px"),
                                    ):
                                        with ui.element("th").style(f"width: {width}"):
                                            ui.label(heading)
                            with ui.element("tbody"):
                                if not items and not state["creating"]:
                                    with ui.element("tr"):
                                        with ui.element("td").props("colspan=5"):
                                            ui.label("No catalog items match this filter.")

                                for item in items:
                                    if state["editing_id"] == item.id:
                                        with ui.element("tr"):
                                            with ui.element("td").props("colspan=5"):
                                                render_editor(item)
                                        continue

                                    selected = item.id == state["selected_id"]
                                    row = ui.element("tr").classes(
                                        "classic-list-row" + (" is-selected" if selected else "")
                                    )
                                    if item.id is not None:
                                        row_elements[item.id] = row
                                    row.on(
                                        "click",
                                        lambda item_id=item.id: select_item(item_id),
                                    ).on(
                                        "dblclick",
                                        lambda item_id=item.id: start_edit(item_id),
                                    )
                                    with row:
                                        with ui.element("td"):
                                            ui.label(
                                                "★" if item.id in favorite_ids else ""
                                            ).classes("classic-favorite-marker")
                                        with ui.element("td"):
                                            ui.label(item.name).classes("font-medium")
                                        with ui.element("td"):
                                            ui.label(item.description or "")
                                        with ui.element("td"):
                                            ui.label(display_price(item.base_price_cents))
                                        with ui.element("td"):
                                            ui.label("Active" if item.active else "Inactive")

                def handle_filter_change(
                    event: events.ValueChangeEventArguments[str | None],
                ) -> None:
                    state["filter"] = event.value or ""
                    visible_ids = {item.id for item in visible_items()}
                    if state["selected_id"] not in visible_ids:
                        state["selected_id"] = None
                        state["editing_id"] = None
                    item_list.refresh()
                    catalog_status.refresh()

                filter_input.on_value_change(handle_filter_change)
                item_list()

            catalog_status()
