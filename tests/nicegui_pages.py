"""Production page registrations for browserless NiceGUI user-story tests."""

from nicegui import ui

from expedite.pages.catalog import register_catalog_page
from expedite.pages.event_details import register_event_details_page
from expedite.pages.events import register_events_page
from expedite.pages.intake import register_intake_page
from expedite.pages.orders import register_orders_page

register_catalog_page()
register_event_details_page()
register_events_page()
register_intake_page(print_label_fn=lambda _: "Test printer")
register_orders_page(print_label_fn=lambda _: "Test printer")
ui.run(native=False, reload=False, show=False)
