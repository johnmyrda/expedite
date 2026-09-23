# Live UI testing approach

This document summarizes the interactive testing used while developing the `win98-gui` branch, the problems encountered, and ways to make the workflow more reliable.

## Current approach

### 1. Use the browser-only preview server

Live UI work uses:

```bash
uv run python scripts/ui_preview.py --port 8765 --data-dir /tmp/expedite-ui-preview
```

This registers the real pages and static theme assets, but runs NiceGUI with `native=False`, `reload=False`, and `show=False`. It avoids opening a pywebview desktop window during routine iteration.

### 2. Test against disposable data

When realistic content is needed, the real usage database is copied into a temporary directory. The original database is never modified or committed.

Temporary copies are then adjusted to create useful scenarios, for example:

- all Quick Add favorites populated;
- inactive catalog items;
- event-price overrides;
- large order lists;
- mixed legacy timestamp formats.

All temporary databases, browser profiles, screenshots, HTML dumps, and logs are kept under `/tmp` and removed afterward.

### 3. Drive headless Chrome through the DevTools protocol

Chrome is launched headlessly with a temporary profile and a remote-debugging port. Small inline Node scripts connect to Chrome using the built-in `WebSocket` implementation and issue Chrome DevTools Protocol commands.

The scripts have been used to:

- navigate among Events, Catalog, Intake, Orders, and Management;
- click controls and edit fields;
- dispatch keyboard and blur events;
- verify database persistence after UI actions;
- inspect DOM text, attributes, classes, and computed CSS;
- measure overflow, table panels, status bars, dialogs, tabs, and buttons;
- exercise viewport widths from normal desktop sizes down to 320 px;
- capture screenshots when visual inspection is useful.

Most checks poll for the required element before interacting rather than assuming the page is immediately ready.

### 4. Run lightweight code checks

During the main UI iteration, the user requested that automated tests not be added or run. Changes were instead accompanied by focused checks such as:

```bash
uv run ruff check <changed files>
uv run python -m py_compile <changed files>
git diff --check
```

A later code-review pass separately ran Ruff, `ty`, the existing pytest suite, and `compileall`; that static review did not launch the application.

### 5. Clean up every process

Preview servers and Chrome are started in the background and tracked by PID. Cleanup uses shell traps where practical, followed by `kill`, `wait`, removal of temporary files, and a process-list check for remaining preview, Chrome, Python spawn, or `resource_tracker` processes.

## Issues encountered

### Native previews left orphaned applications

Early checks launched `src/expedite/main.py`, which always uses `native=True`. NiceGUI/pywebview creates multiprocessing children, and terminating only the apparent parent left several native application copies and Python `spawn`/`resource_tracker` processes running.

This was the reason for creating `scripts/ui_preview.py`. Native mode is now reserved for explicit native-window smoke checks, followed by inspection of the full process tree.

### Headless Chrome does not naturally exit

NiceGUI keeps a WebSocket connection open, so `chrome --headless --dump-dom` can remain alive instead of exiting after the page appears loaded. Reliable cleanup requires launching Chrome in the background and explicitly terminating it.

### Synthetic input can race NiceGUI synchronization

A programmatic `input` event followed by `blur()` in the same JavaScript tick produced a false failure when testing automatic Management price saving. The Python-side field value had not synchronized before the blur handler ran.

Adding a short synchronization delay before blur made the interaction match real typing. A better harness should wait for an observable model update rather than using a fixed delay.

### Test-data assumptions caused false failures

Some checks assumed that the first event contained a price override or that favorites were already populated. The real database did not always contain those states. Disposable scenario setup is now performed explicitly before launching the preview.

### Route construction was initially error-prone

`Event.folder_name` is a method, not a string property, and route segments must be URL-encoded. Using the bound method or an unescaped folder name caused malformed URLs.

### Browser caching hid CSS changes

Reloading a page did not always fetch the latest static stylesheet. Checks now use a fresh browser profile, disable the DevTools cache, add a temporary query string, or restart Chrome when validating CSS.

### Viewport and scrollbar measurements differ

At narrow widths, the document's client width can be smaller than the requested viewport because of the vertical scrollbar. Layout checks therefore compare element bounds, document scroll width, and client width rather than assuming all values equal the requested window width.

### Screenshots alone were insufficient

Screenshots are useful for overall appearance, but they do not reliably prove focus, persistence, overflow, accessibility attributes, or exact dimensions. Computed-style and DOM assertions were used alongside screenshots.

### Text-based selectors are fragile

Several temporary scripts locate controls by labels or `aria-label` values. These break when wording changes. They are acceptable for one-off iteration but not ideal for a durable test suite.

### Live testing found real data-dependent defects

The Orders Submitted sort failure only appeared with a mixture of offset-aware and offset-naive timestamps in realistic data. This reinforced the value of testing disposable copies of actual usage data rather than only empty or newly generated databases.

## Suggested improvements

### Reusable UI-check harness

`scripts/live_ui_harness.py` now owns the complete lifecycle:

1. allocates free preview and DevTools ports;
2. creates a disposable data directory;
3. launches `ui_preview.py` in its own process group;
4. launches headless Chrome with a unique profile;
5. exposes helpers for navigation, evaluation, clicking, screenshots, and polling;
6. retains logs, the DOM, and a screenshot on failure;
7. terminates the full preview and Chrome process groups in `finally`.

Run the current print-lock regression checks with:

```bash
uv run python scripts/live_ui_harness.py
```

Use `--keep-artifacts` to retain successful-run data and logs. Set `CHROME_PATH` when Chrome is not installed in one of the automatically detected locations. The harness records server readiness, Chrome readiness, first-control rendering, NiceGUI handshake, and first-interaction latency in `startup-metrics.json`; `--startup-budget-scale` can adjust the default regression budgets on slower development machines.

### Add named data scenarios

Provide a small scenario generator for states such as:

- empty application;
- realistic populated event;
- maximum favorites;
- inactive catalog items;
- base and overridden event prices;
- many orders;
- legacy timestamps.

The scenarios should always operate on temporary databases.

### Use stable UI selectors

Add `data-testid` attributes to important page roots, dialogs, tables, rows, filters, and primary actions. Accessibility labels should remain user-facing semantics; test IDs can remain stable when wording changes.

### Prefer event-driven waits

Replace fixed sleeps with polling for specific conditions, such as:

- the NiceGUI connection being established;
- a control becoming visible or enabled;
- status-bar text changing;
- a refreshed row acquiring the expected class;
- the copied database containing the expected value.

### Consider Playwright after UI iteration

A browser automation library would simplify lifecycle management, keyboard input, focus checks, screenshots, and assertions. If added, it should be a development-only dependency and should not replace the lightweight preview server.

### Separate browser and native smoke checks

Browser checks should cover page behavior and responsive layout. A smaller native smoke check should separately verify:

- the pywebview window opens;
- File > Exit closes it cleanly;
- no child processes remain;
- packaged static assets and fonts load;
- OS-specific file, print, and window behavior works.

### Standardize the viewport matrix

A repeatable matrix such as 1280, 900, 560, 360, and 320 px would make responsive regressions easier to compare. Each run should record document overflow, status-bar height, tab overflow, and table-panel dimensions.

### Save failure artifacts

On failure, retain the screenshot, current DOM, browser console output, server log, viewport metrics, route, and scenario metadata. On success, delete them to keep `/tmp` clean.

## Limitations

The browser-only preview closely exercises the NiceGUI page code, but it does not validate every native pywebview, packaging, printing, or operating-system integration path. Those require deliberate native testing with stricter process cleanup than routine browser iteration.
