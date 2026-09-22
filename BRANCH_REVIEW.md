# `win98-gui` review handoff

## Goal

Modernize Expedite's desktop UI into a readable Windows-classic interface without simulating a desktop or replacing native window chrome. The application should fill the native window, use cohesive system-gray surfaces, retain white editable/list areas, and prefer system Tahoma with bundled Wine Tahoma fallbacks.

## Major changes

- Added vendored 98.css/theme assets, font fallbacks and licenses, including PyInstaller packaging updates.
- Added shared classic components: menu bar, fixed status bar, group boxes, labeled fields, modal dialogs, sortable headers and keyboard-enabled lists.
- Added shared event navigation for Intake, Orders and Management. These routes now use one consistent event-name header and an attached tab strip.
- Converted Events, Orders, Catalog and Management data to classic tables with selection, contextual toolbars, sticky headers, responsive scrolling and clickable sorting.
- Added Up/Down row selection and Enter activation to Events, Orders and Catalog.
- Kept Catalog favorites inline; inactive rows are gray and Management overrides are yellow rather than using Status columns.
- Converted Catalog Properties, New Event, Receipt Settings and the Intake catalog picker to shared dialogs. Dialogs use OK/Cancel only.
- Added global Receipt Settings, About and File > Exit commands.
- Routed successful operations to the fixed status bar while retaining notifications for validation errors and failures.
- Management prices auto-save on Enter/blur; clearing a value removes the override. Save/reset actions were removed.
- Retained Intake's stacked line-item cards. Favorites are now a compact Quick Add group, customer fields share a row, order number and total share a row, and bottom actions share a row.
- Added `scripts/ui_preview.py` for repeatable browser-only visual review without spawning native windows.

## Intended behavior and constraints

- Do not add fake title bars, desktop backgrounds or an inner simulated window.
- Keep native OS window chrome untouched.
- Preserve inline Catalog favorite stars and selected-row table interactions.
- Preserve automatic Management price saving and the fixed status bar.
- The real usage database is test input only and must never be committed; visual checks used disposable copies.
- Automated tests were intentionally not added or run during UI iteration at the user's request. Ruff, compilation checks and browser interaction checks were used instead.

## Review focus

- NiceGUI refreshable/closure behavior after sorting, selection and auto-saving.
- CSS interaction between Quasar, vendored 98.css and `expedite-98.css`, especially narrow widths and fixed status bars.
- Native File > Exit shutdown behavior and packaged font/static-asset inclusion.
- Dialog focus, validation retention and upload controls.
- Accessibility of icon-only actions and table controls.

## Code-review follow-up

A subsequent code review focused on typed state, Locality of Behaviour, component cohesion,
keyboard behavior and accessibility. The following work was completed:

- Replaced heterogeneous page-state dictionaries with typed dataclasses and `Literal` keys:
  `CatalogPageState`, `EventsPageState`, `OrdersPageState` and `PriceListState`.
- Resolved all `ty` diagnostics and switched notes-height configuration, persistence and UI
  arithmetic to whole integer millimeters. Notes height now has a fixed 60 mm initial default and
  no environment-variable override. File > Exit now uses NiceGUI's typed `app.shutdown()` API.
- Split the former catch-all `pages/components.py` module by responsibility:
  - `pages/classic_ui.py` contains reusable visual primitives and classic dialog behavior.
  - `pages/application_shell.py` contains the application menu, shutdown and status bar.
  - `pages/receipt_settings.py` contains the receipt-settings dialog workflow.
- Kept page-specific event handlers and state close to their controls to preserve Locality of
  Behaviour rather than introducing broad page-controller abstractions.
- Added an explicit `submit_on_enter` dialog option. The searchable Intake catalog picker disables
  default Enter submission so selecting a highlighted option cannot also close the dialog with a
  stale value.
- Added accessible names to icon- and symbol-only controls, including folder, catalog search,
  notes, line removal, receipt open/print and Catalog favorite actions.
- Corrected the README to document system Tahoma with bundled Wine Tahoma fallbacks instead of
  describing Pixelated MS Sans Serif as the active interface font.
- Made catalog-item and favorite updates atomic within one transaction. A regression test verifies
  that an item edit is rolled back if the favorite limit prevents the favorite change.

Review validation completed without launching the application:

- `uv run ruff check .` passed.
- `uv run ty check` passed.
- `uv run pytest -q` passed with 27 tests.
- `uv run python -m compileall -q src scripts` passed.
- `git diff --check` passed.

The follow-up review found no remaining merge-blocking issues. Live or interactive application
validation was intentionally not performed.

## Deferred work

- Intake initial focus and tab-order review.
- Optional Ctrl+Enter submission shortcut.
- General dirty-form navigation warnings.
- Final accessibility semantics such as `aria-selected`, `aria-sort`, keyboard-accessible truncation help and inactive-state contrast review.
