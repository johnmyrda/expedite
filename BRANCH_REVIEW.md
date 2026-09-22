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

## Deferred work

- Intake initial focus and tab-order review.
- Optional Ctrl+Enter submission shortcut.
- General dirty-form navigation warnings.
- Final accessibility semantics such as `aria-selected`, `aria-sort`, keyboard-accessible truncation help and inactive-state contrast review.
