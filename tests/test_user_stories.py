"""Complete user journeys through real NiceGUI pages and disposable persistence.

The User fixture exercises Python-side page interactions. Browser-only focus, blur,
scrolling, and print timing remain covered by scripts/live_ui_harness.py.
"""

import asyncio
import csv
from collections.abc import Iterator
from pathlib import Path

import pytest
from nicegui.element import Element
from nicegui.elements.button import Button
from nicegui.elements.dialog import Dialog
from nicegui.elements.input import Input
from nicegui.elements.item import Item, ItemSection
from nicegui.elements.label import Label
from nicegui.elements.tabs import Tab
from nicegui.testing import User

from expedite.storage.database import dispose_engine
from expedite.storage.events import list_events
from expedite.storage.sqlite_store import (
    ORDERS_CSV_FILENAME,
    event_catalog_prices,
    get_order,
    list_catalog_favorite_ids,
    list_catalog_items,
    list_order_records,
)

pytestmark = [pytest.mark.anyio, pytest.mark.nicegui_main_file("tests/nicegui_pages.py")]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("EVENT_INTAKE_DATA_DIR", str(tmp_path))
    dispose_engine()
    yield
    dispose_engine()


def _field(user: User, label: str) -> Input:
    for element in user.current_layout.descendants():
        if isinstance(element, Label) and element.text == label:
            parent = element.parent_slot.parent if element.parent_slot else None
            if parent is not None:
                for child in parent.descendants():
                    if isinstance(child, Input):
                        return child
    raise AssertionError(f"No input found for {label}")


def _button(user: User, aria_label: str) -> Button:
    buttons = [
        element for element in user.current_layout.descendants()
        if isinstance(element, Button)
    ]
    for button in buttons:
        if button.props.get("aria-label") == aria_label:
            return button
    raise AssertionError(
        f"No button named {aria_label!r}; available labels: "
        f"{[button.props.get('aria-label') for button in buttons]}\n{user.current_layout}"
    )


def _dialog_button(user: User, title: str, action: str) -> Button:
    return next(
        button
        for dialog in user.current_layout.descendants()
        if isinstance(dialog, Dialog)
        and any(isinstance(child, Label) and child.text == title for child in dialog.descendants())
        for button in dialog.descendants()
        if isinstance(button, Button) and button.props.get("label") == action
    )


def _item_row(user: User, item_name: str) -> Element:
    return next(
        element
        for element in user.current_layout.descendants()
        if element.tag == "tr"
        and any(
            isinstance(child, Label) and child.text == item_name
            for child in element.descendants()
        )
    )


def _click(user: User, element: Element, marker: str) -> None:
    element.mark(marker)
    user.find(marker=marker).click()


def _set_field(user: User, label: str, value: str) -> None:
    with user:
        _field(user, label).value = value


async def _return_to_events(user: User) -> None:
    events_item = next(
        element for element in user.current_layout.descendants()
        if isinstance(element, Item)
        and any(
            isinstance(child, ItemSection) and child.text == "Events"
            for child in element.descendants()
        )
    )
    _click(user, events_item, "events-menu")
    await user.should_see("New Event...")


async def _create_event(user: User, name: str) -> None:
    _click(user, next(iter(user.find(kind=Button, content="New Event...").elements)), "new-event")
    _set_field(user, "Event name", name)
    _set_field(user, "Start date", "2026-10-01")
    _click(user, _dialog_button(user, "New Event", "Create"), "create-event")
    await user.should_see("Order #1")
    assert [event.name for event in list_events()] == [name]


async def _create_catalog_item(user: User, name: str, price: str) -> int:
    user.find(kind=Button, content="New...").click()
    _set_field(user, "Name", name)
    _set_field(user, "Base price", price)
    _click(user, _dialog_button(user, "Catalog Item Properties", "OK"), "save-item")
    await user.should_see("Catalog item saved")
    matching = [item for item in list_catalog_items() if item.name == name]
    assert len(matching) == 1 and matching[0].id is not None
    return matching[0].id


async def _submit_ticket(user: User, name: str, item: str, price: str, number: int) -> None:
    _set_field(user, "Name", name)
    _set_field(user, "Phone", "555-0100")
    _set_field(user, "Item / description", item)
    _set_field(user, "Unit price", price)
    _click(user, _button(user, "Submit Order"), f"submit-{number}")
    await user.should_see(f"Order #{number} receipt", retries=30)
    await user.should_see(f"Order #{number + 1}", retries=30)


async def test_user_creates_event_submits_three_tickets_and_exports_csv(user: User) -> None:
    await user.open("/")
    await _create_event(user, "Autumn Fair")
    event = list_events()[0]

    for number, (name, item, price) in enumerate(
        (("Ada", "Blue Mug", "12.50"), ("Ben", "Red Shirt", "8.00"),
         ("Cleo", "Tea Cup", "4.25")),
        start=1,
    ):
        await _submit_ticket(user, name, item, price, number)

    user.find(kind=Tab, content="Orders").click()
    await user.should_see("Export...")
    user.find(kind=Button, content="Export...").click()
    await user.should_see("Orders exported")

    with (event.path / ORDERS_CSV_FILENAME).open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert [(row["order_number"], row["customer_name"], row["order_total"])
            for row in rows] == [("1", "Ada", "12.50"), ("2", "Ben", "8.00"),
                                ("3", "Cleo", "4.25")]
    assert [row["line_items"] for row in rows] == [
        "1 x Blue Mug @ 12.50", "1 x Red Shirt @ 8.00", "1 x Tea Cup @ 4.25",
    ]
    assert len(list_order_records(event)) == 3


async def test_user_edits_a_ticket_and_exports_the_updated_order(user: User) -> None:
    await user.open("/")
    await _create_event(user, "Edit Fair")
    event = list_events()[0]
    await _submit_ticket(user, "Ada", "Blue Mug", "12.50", 1)

    user.find(kind=Tab, content="Orders").click()
    await user.should_see("Export...")
    _click(user, _item_row(user, "Ada"), "select-ada")
    user.find(kind=Button, content="Edit...").click()
    await user.should_see("Edit Order #1")
    _set_field(user, "Unit price", "9.00")
    _click(user, _button(user, "Save Changes"), "save-changes")
    await user.should_see("Order #1 receipt", retries=30)

    user.find(kind=Tab, content="Orders").click()
    await user.should_see("Export...")
    user.find(kind=Button, content="Export...").click()
    await user.should_see("Orders exported")
    with (event.path / ORDERS_CSV_FILENAME).open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 1
    assert (rows[0]["customer_name"], rows[0]["order_total"], rows[0]["line_items"]) == (
        "Ada", "9.00", "1 x Blue Mug @ 9.00",
    )
    order = get_order(event, 1)
    assert order is not None and order.line_items[0].unit_price_cents == 900


async def test_user_sets_event_override_and_uses_it_on_a_ticket(user: User) -> None:
    await user.open("/catalog")
    item_id = await _create_catalog_item(user, "Blue Mug", "12.50")
    await _return_to_events(user)
    await _create_event(user, "Override Fair")
    event = list_events()[0]

    user.find(kind=Tab, content="Management").click()
    await user.should_see("Catalog Price Overrides")
    price_field = next(
        element for element in user.current_layout.descendants()
        if isinstance(element, Input)
        and element.props.get("aria-label") == "Event price for Blue Mug"
    )
    with user:
        price_field.value = "7.00"
    price_field.mark("save-price")
    user.find(marker="save-price").trigger("keydown.enter.prevent")
    await user.should_see("Override saved")
    assert event_catalog_prices(event) == {item_id: 700}

    user.find(kind=Tab, content="Intake").click()
    await user.should_see("Order #1")
    _click(user, _button(user, "Search catalog for line 1"), "catalog-picker")
    await user.should_see("Select Catalog Item")
    await user.should_see("$7.00")
    _click(user, _item_row(user, "Blue Mug"), "choose-item")
    select_button = _dialog_button(user, "Select Catalog Item", "Select")
    for _ in range(30):
        if select_button.enabled:
            break
        await asyncio.sleep(0.01)
    else:
        raise AssertionError("Selecting a catalog row did not enable Select")
    _click(user, select_button, "confirm-item")
    await user.should_see("Total: $7.00")
    _set_field(user, "Name", "Ada")
    _set_field(user, "Phone", "555-0100")
    _click(user, _button(user, "Submit Order"), "submit-override")
    await user.should_see("Order #1 receipt", retries=30)

    order = get_order(event, 1)
    assert order is not None and order.cost == "7.00"
    assert len(order.line_items) == 1
    assert (order.line_items[0].catalog_item_id, order.line_items[0].unit_price_cents) == (
        item_id, 700,
    )


async def test_user_favorites_item_then_uses_quick_add_on_intake(user: User) -> None:
    await user.open("/catalog")
    item_id = await _create_catalog_item(user, "Blue Mug", "12.50")
    await user.should_see(kind=Button, content="☆", retries=30)
    # User.click() dispatches "click", but this control listens on "click.stop".
    favorite_button = _button(user, "Add to intake favorites: Blue Mug")
    favorite_button.mark("favorite-mug")
    user.find(marker="favorite-mug").trigger("click.stop")
    await user.should_see("Added to intake favorites")
    assert item_id in list_catalog_favorite_ids()

    await _return_to_events(user)
    await _create_event(user, "Favorites Fair")
    event = list_events()[0]
    _click(user, _button(user, "Blue Mug · No description · Cost: $12.50"), "quick-add")
    await user.should_see("Total: $12.50")
    _set_field(user, "Name", "Ben")
    _set_field(user, "Phone", "555-0100")
    _click(user, _button(user, "Submit Order"), "submit-favorite")
    await user.should_see("Order #1 receipt", retries=30)

    order = get_order(event, 1)
    assert order is not None and order.cost == "12.50"
    assert len(order.line_items) == 1
    assert (order.line_items[0].catalog_item_id, order.line_items[0].description) == (
        item_id, "Blue Mug",
    )
