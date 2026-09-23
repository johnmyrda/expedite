"""Catalog management page."""

from dataclasses import dataclass
from typing import Literal

from nicegui import events, ui
from nicegui.element import Element

from expedite.config import APP_NAME
from expedite.models import CatalogItem
from expedite.money import display_price, parse_price_cents
from expedite.pages.application_shell import (
    ApplicationStatus,
    application_menu,
    application_status,
)
from expedite.pages.classic_ui import (
    adjacent_list_value,
    classic_dialog,
    enable_list_keyboard,
    group_box,
    labeled_field,
    sortable_header,
    update_list_row_selection,
)
from expedite.storage.sqlite_store import (
    MAX_CATALOG_FAVORITES,
    list_catalog_favorite_ids,
    list_catalog_items,
    save_catalog_item,
    set_catalog_item_favorite,
)

CatalogSortKey = Literal["favorite", "name", "description", "price"]


@dataclass
class CatalogPageState:
    """Mutable state for catalog filtering, selection, editing, and sorting."""

    filter: str = ""
    selected_id: int | None = None
    dialog_item_id: int | None = None
    sort_key: CatalogSortKey = "name"
    sort_descending: bool = False


def register_catalog_page() -> None:
    @ui.page("/catalog")
    def catalog_page() -> None:
        ui.page_title(f"{APP_NAME} - Catalog")

        state = CatalogPageState()
        status = ApplicationStatus()

        def visible_items() -> list[CatalogItem]:
            query = state.filter.strip().casefold()
            return [
                item
                for item in list_catalog_items()
                if not query
                or query in item.name.casefold()
                or query in (item.description or "").casefold()
            ]

        def selected_item() -> CatalogItem | None:
            selected_id = state.selected_id
            return next(
                (item for item in list_catalog_items() if item.id == selected_id),
                None,
            )

        def update_status() -> None:
            item = selected_item()
            favorite_count = len(list_catalog_favorite_ids())
            detail = (
                f"{item.name} selected · {favorite_count}/{MAX_CATALOG_FAVORITES} favorites"
                if item is not None
                else f"{len(visible_items())} item(s) · "
                f"{favorite_count}/{MAX_CATALOG_FAVORITES} favorites"
            )
            status.update("Ready", detail)

        def refresh_catalog() -> None:
            item_list.refresh()
            update_status()

        def focus(element: Element) -> None:
            ui.timer(0.05, lambda: element.run_method("focus"), once=True)

        def save_dialog() -> None:
            name = (name_input.value or "").strip()
            if not name:
                ui.notify("Name is required.", type="negative")
                focus(name_input)
                return
            try:
                price_cents = parse_price_cents(price_input.value)
            except ValueError as error:
                ui.notify(str(error), type="negative")
                focus(price_input)
                return

            favorite_ids = set(list_catalog_favorite_ids())
            was_favorite = state.dialog_item_id in favorite_ids
            wants_favorite = bool(favorite_input.value)
            if wants_favorite and not active_input.value:
                ui.notify("Inactive catalog items cannot be favorited.", type="negative")
                focus(favorite_input)
                return
            if wants_favorite and not was_favorite and len(favorite_ids) >= MAX_CATALOG_FAVORITES:
                ui.notify(
                    f"No more than {MAX_CATALOG_FAVORITES} catalog items can be favorited.",
                    type="negative",
                )
                focus(favorite_input)
                return

            try:
                saved = save_catalog_item(
                    item_id=state.dialog_item_id,
                    name=name,
                    description=(description_input.value or "").strip() or None,
                    base_price_cents=price_cents,
                    active=bool(active_input.value),
                    favorite=wants_favorite,
                )
            except ValueError as error:
                ui.notify(str(error), type="negative")
                return

            state.selected_id = saved.id
            state.dialog_item_id = saved.id
            refresh_catalog()
            status.update("Catalog item saved", saved.name)
            item_dialog.close()

        with classic_dialog(
            "Catalog Item Properties",
            on_accept=save_dialog,
            width="560px",
        ) as item_dialog:
            with group_box("General"):
                with ui.row().classes("w-full items-end gap-3 flex-wrap"):
                    with labeled_field("Name", classes="grow min-w-64"):
                        name_input = (
                            ui.input().props("outlined dense maxlength=120").classes("w-full")
                        )
                    with labeled_field("Base price", classes="w-36"):
                        price_input = (
                            ui.input()
                            .props("outlined dense prefix=$ inputmode=decimal")
                            .classes("w-full")
                        )
                with labeled_field("Description"):
                    description_input = (
                        ui.textarea().props("outlined dense autogrow").classes("w-full")
                    )
                with ui.row().classes("items-center gap-6"):
                    active_input = ui.checkbox("Active", value=True)
                    favorite_input = ui.checkbox("Favorite", value=False)
            item_dialog.set_initial_focus(name_input)

        def configure_favorite_input() -> None:
            favorite_ids = set(list_catalog_favorite_ids())
            already_favorite = state.dialog_item_id in favorite_ids
            can_favorite = already_favorite or len(favorite_ids) < MAX_CATALOG_FAVORITES
            favorite_input.set_enabled(bool(active_input.value) and can_favorite)

        def handle_active_change(
            event: events.ValueChangeEventArguments[bool | None],
        ) -> None:
            if not event.value:
                favorite_input.value = False
            configure_favorite_input()

        active_input.on_value_change(handle_active_change)

        def open_item_dialog(item: CatalogItem | None) -> None:
            state.dialog_item_id = item.id if item is not None else None
            name_input.value = item.name if item is not None else ""
            description_input.value = item.description or "" if item is not None else ""
            price_input.value = f"{item.base_price_cents / 100:.2f}" if item is not None else ""
            active_input.value = item.active if item is not None else True
            favorite_input.value = item is not None and item.id in set(list_catalog_favorite_ids())
            configure_favorite_input()
            item_dialog.open()

        with ui.column().classes("app-page catalog-page w-full p-6 gap-6"):
            application_menu(status)
            with ui.row().classes("app-page-header w-full items-center justify-between"):
                ui.label("Catalog").classes("app-page-title text-3xl font-bold")

            with group_box("Catalog Items"):
                with labeled_field("Filter by name or description"):
                    filter_input = ui.input().props("outlined clearable").classes("w-full")

                @ui.refreshable
                def item_list() -> None:
                    items = visible_items()
                    favorite_ids = set(list_catalog_favorite_ids())
                    sort_key = state.sort_key
                    key_functions = {
                        "favorite": lambda item: item.id in favorite_ids,
                        "name": lambda item: item.name.casefold(),
                        "description": lambda item: (item.description or "").casefold(),
                        "price": lambda item: item.base_price_cents,
                    }
                    items.sort(
                        key=key_functions[sort_key],
                        reverse=state.sort_descending,
                    )
                    row_elements = {}

                    def current_item() -> CatalogItem | None:
                        return next(
                            (item for item in items if item.id == state.selected_id),
                            None,
                        )

                    def configure_toolbar() -> None:
                        item = current_item()
                        active_button.set_text(
                            "Deactivate" if item is None or item.active else "Activate"
                        )
                        edit_button.enabled = item is not None
                        active_button.enabled = item is not None

                    def select_item(item_id: int | None) -> None:
                        if item_id is not None:
                            update_list_row_selection(
                                catalog_table,
                                row_elements,
                                previous=state.selected_id,
                                selected=item_id,
                            )
                        state.selected_id = item_id
                        configure_toolbar()
                        update_status()

                    def start_edit(item_id: int | None = None) -> None:
                        selected_id = item_id if item_id is not None else state.selected_id
                        if selected_id is None:
                            return
                        item = next(
                            (candidate for candidate in items if candidate.id == selected_id),
                            None,
                        )
                        if item is None:
                            return
                        select_item(selected_id)
                        open_item_dialog(item)

                    def move_selection(offset: int) -> None:
                        item_ids = [item.id for item in items if item.id is not None]
                        item_id = adjacent_list_value(item_ids, state.selected_id, offset)
                        if item_id is None:
                            return
                        select_item(item_id)
                        row_elements[item_id].run_method(
                            "scrollIntoView", {"block": "nearest"}
                        )

                    def set_favorite(item: CatalogItem, favorite: bool) -> None:
                        if item.id is None:
                            return
                        try:
                            set_catalog_item_favorite(item.id, favorite)
                        except ValueError as error:
                            ui.notify(str(error), type="negative")
                        else:
                            action = "Added to" if favorite else "Removed from"
                            refresh_catalog()
                            status.update(f"{action} intake favorites", item.name)

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
                        refresh_catalog()
                        status.update(action, saved.name)

                    with ui.row().classes("classic-list-toolbar w-full items-center gap-1"):
                        ui.button("New...", on_click=lambda: open_item_dialog(None)).props(
                            "flat dense"
                        )
                        edit_button = ui.button("Edit...", on_click=lambda: start_edit()).props(
                            "flat dense"
                        )
                        ui.element("div").classes("classic-toolbar-separator")
                        active_button = ui.button("Deactivate", on_click=toggle_active).props(
                            "flat dense"
                        )
                        configure_toolbar()

                    def change_sort(sort_key: CatalogSortKey) -> None:
                        if state.sort_key == sort_key:
                            state.sort_descending = not state.sort_descending
                        else:
                            state.sort_key = sort_key
                            state.sort_descending = False
                        item_list.refresh()

                    with (
                        ui.element("div").classes("classic-list-panel page-scroll-list"),
                        ui.element("table")
                        .classes("classic-list catalog-list")
                        .props('aria-label="Catalog items"') as catalog_table,
                    ):
                        enable_list_keyboard(
                            catalog_table,
                            on_move=move_selection,
                            on_activate=lambda: start_edit(),
                        )
                        with ui.element("thead"), ui.element("tr"):
                            for heading, column_key, width in (
                                ("Favorite", "favorite", "86px"),
                                ("Name", "name", "24%"),
                                ("Description", "description", "auto"),
                                ("Price", "price", "120px"),
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
                                    ui.element("td").props("colspan=4"),
                                ):
                                    ui.label("No catalog items match this filter.")

                            for item in items:
                                selected = item.id == state.selected_id
                                row = ui.element("tr").classes(
                                    "classic-list-row"
                                    + (" is-selected" if selected else "")
                                    + (" is-inactive" if not item.active else "")
                                )
                                if not item.active:
                                    row.props('title="Inactive catalog item"')
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
                                    with ui.element("td").classes("classic-actions"):
                                        is_favorite = item.id in favorite_ids

                                        def handle_favorite(
                                            selected_item: CatalogItem = item,
                                            favorite: bool = not is_favorite,
                                        ) -> None:
                                            set_favorite(selected_item, favorite)

                                        favorite_button = (
                                            ui.button("★" if is_favorite else "☆")
                                            .props("flat round dense")
                                            .classes("classic-favorite-button")
                                            .on("click.stop", handle_favorite)
                                        )
                                        favorite_action = (
                                            "Remove from intake favorites"
                                            if is_favorite
                                            else "Add to intake favorites"
                                        )
                                        favorite_button.props["aria-label"] = (
                                            f"{favorite_action}: {item.name}"
                                        )
                                        favorite_button.tooltip(favorite_action)
                                        if not item.active or (
                                            not is_favorite
                                            and len(favorite_ids) >= MAX_CATALOG_FAVORITES
                                        ):
                                            favorite_button.disable()
                                    with ui.element("td"):
                                        ui.label(item.name).classes("font-medium")
                                    with ui.element("td"):
                                        ui.label(item.description or "")
                                    with ui.element("td"):
                                        ui.label(display_price(item.base_price_cents))

                def handle_filter_change(
                    event: events.ValueChangeEventArguments[str | None],
                ) -> None:
                    state.filter = event.value or ""
                    visible_ids = {item.id for item in visible_items()}
                    if state.selected_id not in visible_ids:
                        state.selected_id = None
                    item_list.refresh()
                    update_status()

                filter_input.on_value_change(handle_filter_change)
                item_list()

            update_status()
            application_status(status)
