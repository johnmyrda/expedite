"""Reusable Windows-classic presentation components."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from nicegui import ui
from nicegui.element import Element
from nicegui.elements.button import Button
from nicegui.elements.dialog import Dialog


@contextmanager
def group_box(title: str) -> Iterator[None]:
    """Render a classic labeled group box."""
    with ui.element("fieldset").classes("classic-group w-full"):
        with ui.element("legend").classes("classic-group-legend"):
            ui.label(title)
        yield


@contextmanager
def labeled_field(label: str, *, classes: str = "w-full") -> Iterator[None]:
    """Render an explicit label above a form control."""
    with ui.column().classes(f"classic-field gap-1 {classes}"):
        ui.label(label).classes("classic-field-label")
        yield


def sortable_header(
    label: str,
    *,
    active: bool,
    descending: bool,
    on_click: Callable[[], None],
) -> None:
    """Render an accessible classic list header which controls sorting."""
    indicator = " ▼" if descending else " ▲"
    button = (
        ui.button(f"{label}{indicator if active else ''}", on_click=on_click)
        .props("flat dense no-caps")
        .classes("classic-sort-header w-full")
    )
    direction = "descending" if descending else "ascending"
    button.props["aria-label"] = (
        f"Sort by {label}" if not active else f"Sort by {label}, currently {direction}"
    )


def enable_list_keyboard(list_element: Element) -> None:
    """Enable classic Up/Down selection and Enter activation on a list table."""
    list_element.props("tabindex=0")
    list_element.on(
        "click",
        js_handler=(
            "(event) => { if (event.target.closest('.classic-list-row')) "
            "event.currentTarget.focus(); }"
        ),
    )
    list_element.on(
        "keydown",
        js_handler="""
        (event) => {
            if (event.target !== event.currentTarget) return;
            const rows = [...event.currentTarget.querySelectorAll('.classic-list-row')];
            if (!rows.length) return;
            const selectedIndex = rows.findIndex(row => row.classList.contains('is-selected'));
            if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                const offset = event.key === 'ArrowDown' ? 1 : -1;
                const fallback = event.key === 'ArrowDown' ? 0 : rows.length - 1;
                const nextIndex = selectedIndex < 0
                    ? fallback
                    : Math.min(Math.max(selectedIndex + offset, 0), rows.length - 1);
                rows[nextIndex].click();
                rows[nextIndex].scrollIntoView({block: 'nearest'});
            } else if (event.key === 'Enter' && selectedIndex >= 0) {
                event.preventDefault();
                rows[selectedIndex].dispatchEvent(new MouseEvent('dblclick', {
                    bubbles: true,
                    cancelable: true,
                }));
            }
        }
        """,
    )


@dataclass
class ClassicDialog:
    """Controller for a reusable classic modal dialog."""

    element: Dialog
    default_button: Button | None = None
    initial_focus: Element | None = None

    def __post_init__(self) -> None:
        self.element.on("show", self._focus_initial_control)

    def _focus_initial_control(self) -> None:
        if self.initial_focus is not None:
            self.initial_focus.run_method("focus")

    def set_initial_focus(self, element: Element) -> None:
        """Set the control which receives focus when the dialog opens."""
        self.initial_focus = element

    def open(self) -> None:
        """Open the dialog; its show event moves focus to the initial control."""
        self.element.open()

    def close(self) -> None:
        """Close the dialog."""
        self.element.close()


@contextmanager
def classic_dialog(
    title: str,
    *,
    accept_label: str = "OK",
    cancel_label: str | None = "Cancel",
    on_accept: Callable[[], object] | None = None,
    width: str = "520px",
    submit_on_enter: bool = True,
    footer_text: str | None = None,
) -> Iterator[ClassicDialog]:
    """Render a classic modal with standard actions and optional Enter submission."""
    dialog = ui.dialog()
    controller = ClassicDialog(dialog)

    def accept() -> object | None:
        if on_accept is None:
            dialog.close()
            return None
        return on_accept()

    with (
        dialog,
        ui.card()
        .classes("classic-dialog")
        .style(f"width: min({width}, calc(100vw - 32px))") as card,
    ):
        ui.label(title).classes("classic-dialog-title")
        ui.separator()
        with ui.column().classes("classic-dialog-body w-full"):
            yield controller
        ui.separator()
        with ui.row().classes("classic-dialog-actions w-full items-center gap-2"):
            if footer_text is not None:
                ui.label(footer_text).classes("text-sm")
            ui.space()
            default_button_props = "color=primary"
            if controller.initial_focus is None:
                default_button_props += " autofocus"
            controller.default_button = (
                ui.button(accept_label, on_click=accept)
                .props(default_button_props)
                .classes("classic-default-button")
            )
            if cancel_label is not None:
                ui.button(cancel_label, on_click=dialog.close).props("flat")

        if submit_on_enter:
            card.on(
                "keydown",
                js_handler=(
                    "(event) => {"
                    " if (event.key === 'Enter'"
                    " && event.target.tagName !== 'TEXTAREA'"
                    " && event.target.tagName !== 'BUTTON') {"
                    " event.preventDefault();"
                    f" document.getElementById('{controller.default_button.html_id}')?.click();"
                    " }"
                    "}"
                ),
            )
