"""Windows 98 visual theme integration for NiceGUI."""

from pathlib import Path

from nicegui import app, ui

_THEME_ROUTE = "/expedite-static"
_STATIC_DIR = Path(__file__).with_name("static")


def register_theme_assets() -> None:
    """Serve theme assets and add the application CSS to every page once."""
    app.add_static_files(_THEME_ROUTE, _STATIC_DIR)
    ui.add_css(_STATIC_DIR / "98.css", shared=True)
    ui.add_css(_STATIC_DIR / "expedite-98.css", shared=True)
