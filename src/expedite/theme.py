"""Windows 98 visual theme integration for NiceGUI."""

from pathlib import Path

from nicegui import app, ui

_THEME_ROUTE = "/expedite-static"
_STATIC_DIR = Path(__file__).with_name("static")


def register_theme_assets() -> None:
    """Serve vendored theme assets without requiring internet access."""
    app.add_static_files(_THEME_ROUTE, _STATIC_DIR)


def apply_windows_98_theme() -> None:
    """Load 98.css and the NiceGUI compatibility layer for the current page."""
    ui.add_head_html(
        f'<link rel="stylesheet" href="{_THEME_ROUTE}/98.css">'
        f'<link rel="stylesheet" href="{_THEME_ROUTE}/expedite-98.css">'
    )
