"""Catalog management page."""

from nicegui import events, ui
from nicegui.element import Element

from expedite.config import APP_NAME
from expedite.models import CatalogItem
from expedite.money import display_price, parse_price_cents
from expedite.pages.components import (
    application_menu,
    application_status,
    classic_dialog,
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

        state: dict[str, int | str | None] = {
            "filter": "",
            "selected_id": None,
            "dialog_item_id": None,
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

        def refresh_catalog() -> None:
            item_list.refresh()
            catalog_status.refresh()

        def focus(element: Element) -> None:
            ui.timer(0.05, lambda: element.run_method("focus"), once=True)

        def save_dialog(*, close: bool) -> None:
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
            was_favorite = state["dialog_item_id"] in favorite_ids
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
                    item_id=state["dialog_item_id"],
                    name=name,
                    description=(description_input.value or "").strip() or None,
                    base_price_cents=price_cents,
                    active=bool(active_input.value),
                )
                if saved.id is not None:
                    set_catalog_item_favorite(saved.id, wants_favorite)
            except ValueError as error:
                ui.notify(str(error), type="negative")
                return

            state["selected_id"] = saved.id
            state["dialog_item_id"] = saved.id
            ui.notify(f"Saved {saved.name}", type="positive")
            refresh_catalog()
            if close:
                item_dialog.close()

        with classic_dialog(
            "Catalog Item Properties",
            on_accept=lambda: save_dialog(close=True),
            on_apply=lambda: save_dialog(close=False),
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
            already_favorite = state["dialog_item_id"] in favorite_ids
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
            state["dialog_item_id"] = item.id if item is not None else None
            name_input.value = item.name if item is not None else ""
            description_input.value = item.description or "" if item is not None else ""
            price_input.value = f"{item.base_price_cents / 100:.2f}" if item is not None else ""
            active_input.value = item.active if item is not None else True
            favorite_input.value = item is not None and item.id in set(list_catalog_favorite_ids())
            configure_favorite_input()
            if item_dialog.apply_button is not None:
                item_dialog.apply_button.set_visibility(item is not None)
            item_dialog.open()

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

                    def configure_toolbar() -> None:
                        item = current_item()
                        active_button.set_text(
                            "Deactivate" if item is None or item.active else "Activate"
                        )
                        edit_button.enabled = item is not None
                        active_button.enabled = item is not None

                    def select_item(item_id: int | None) -> None:
                        previous_id = state["selected_id"]
                        if previous_id in row_elements:
                            row_elements[previous_id].classes(remove="is-selected")
                        state["selected_id"] = item_id
                        if item_id in row_elements:
                            row_elements[item_id].classes(add="is-selected")
                        configure_toolbar()
                        catalog_status.refresh()

                    def start_edit(item_id: int | None = None) -> None:
                        selected_id = item_id if item_id is not None else state["selected_id"]
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

                    def set_favorite(item: CatalogItem, favorite: bool) -> None:
                        if item.id is None:
                            return
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

                    with (
                        ui.element("div").classes("classic-list-panel"),
                        ui.element("table").classes("classic-list"),
                    ):
                        with ui.element("thead"), ui.element("tr"):
                            for heading, width in (
                                ("Favorite", "86px"),
                                ("Name", "24%"),
                                ("Description", "auto"),
                                ("Price", "120px"),
                                ("Status", "100px"),
                            ):
                                with ui.element("th").style(f"width: {width}"):
                                    ui.label(heading)
                        with ui.element("tbody"):
                            if not items:
                                with (
                                    ui.element("tr"),
                                    ui.element("td").props("colspan=5"),
                                ):
                                    ui.label("No catalog items match this filter.")

                            for item in items:
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
                                            .on(
                                                "click",
                                                handle_favorite,
                                                js_handler=(
                                                    "(event) => { "
                                                    "event.stopPropagation(); emit(); }"
                                                ),
                                            )
                                        )
                                        favorite_button.tooltip(
                                            "Remove from intake favorites"
                                            if is_favorite
                                            else "Add to intake favorites"
                                        )
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
                                    with ui.element("td"):
                                        ui.label("Active" if item.active else "Inactive")

                def handle_filter_change(
                    event: events.ValueChangeEventArguments[str | None],
                ) -> None:
                    state["filter"] = event.value or ""
                    visible_ids = {item.id for item in visible_items()}
                    if state["selected_id"] not in visible_ids:
                        state["selected_id"] = None
                    item_list.refresh()
                    catalog_status.refresh()

                filter_input.on_value_change(handle_filter_change)
                item_list()

            catalog_status()
