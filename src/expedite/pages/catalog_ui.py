"""Catalog-specific presentation shared by the catalog views."""

from collections.abc import Mapping

from nicegui import ui

from expedite.models import CatalogItem


def catalog_item_matches(item: CatalogItem, query: str) -> bool:
    """Match a catalog item's name or description, ignoring case and surrounding spaces."""
    text = query.strip().casefold()
    return not text or text in item.name.casefold() or text in (item.description or "").casefold()


def effective_event_price_cents(item: CatalogItem, overrides: Mapping[int, int]) -> int:
    """Return the event price when overridden, otherwise the catalog base price."""
    if item.id is None:
        return item.base_price_cents
    return overrides.get(item.id, item.base_price_cents)


def compact_catalog_item(item: CatalogItem) -> None:
    """Render a catalog item name with its description beneath it in one cell."""
    ui.label(item.name).classes("font-medium")
    if item.description:
        ui.label(item.description).classes("catalog-item-description")
