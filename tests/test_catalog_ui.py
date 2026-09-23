"""Catalog presentation rules shared by the three catalog views."""

from expedite.models import CatalogItem
from expedite.pages.catalog_ui import catalog_item_matches, effective_event_price_cents


def test_catalog_item_matches_name_description_and_empty_query() -> None:
    item = CatalogItem(name="Blue Mug", description="Handmade Ceramic", base_price_cents=1250)

    assert catalog_item_matches(item, "  BLUE  ")
    assert catalog_item_matches(item, "ceramic")
    assert catalog_item_matches(item, "   ")
    assert not catalog_item_matches(item, "shirt")
    assert not catalog_item_matches(
        CatalogItem(name="Blue Mug", description=None, base_price_cents=1250),
        "ceramic",
    )


def test_effective_event_price_uses_override_or_base_price() -> None:
    saved = CatalogItem(id=7, name="Blue Mug", base_price_cents=1250)
    unsaved = CatalogItem(name="New Item", base_price_cents=500)

    assert effective_event_price_cents(saved, {7: 0}) == 0
    assert effective_event_price_cents(saved, {8: 900}) == 1250
    assert effective_event_price_cents(unsaved, {7: 0}) == 500
