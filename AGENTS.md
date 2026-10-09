# AGENTS.md

## Project overview

Expedite is an offline-first desktop application for event order intake. It uses Python 3.11+, NiceGUI in native mode, SQLModel/SQLite for persistence, Pillow for receipt images, and PyInstaller for distribution. Windows is the primary deployment target, while development commonly happens on macOS.

Treat `README.md`, `DEVELOPMENT.md`, the implementation, and the tests as the current source of truth. `EVENT_INTAKE.md` is an early product specification and contains superseded details, including the original label size and printing scope.

## Repository map

- `src/expedite/main.py`: application startup and page registration.
- `src/expedite/pages/`: NiceGUI routes and interface composition.
- `src/expedite/models/`: SQLModel domain entities.
- `src/expedite/storage/`: SQLite engine, repositories, event directories, exports, and settings.
- `src/expedite/label.py`: thermal receipt image generation.
- `src/expedite/printing.py`: Windows ESC/POS print dispatch.
- `src/expedite/static/`: vendored theme, compatibility CSS, fonts, and licenses.
- `tests/`: unit, browserless NiceGUI, startup, and integration tests.
- `scripts/ui_preview.py`: browser-only development server using real pages.
- `scripts/live_ui_harness.py`: opt-in headless-browser checks with disposable data.
- `build/`: PyInstaller specifications, Windows launchers, and installer definition.

## Development commands

Use `uv` for environments and commands:

```bash
uv sync
uv run expedite
```

Run the standard quality checks used by CI:

```bash
uv run ruff check .
uv run ty check
uv run pytest
```

Run a focused test during iteration when appropriate, then run the full relevant suite before handing off a substantive change:

```bash
uv run pytest tests/test_validation.py
```

Live browser checks are opt-in and require Chrome or Chromium:

```bash
uv run python scripts/live_ui_harness.py
EXPEDITE_LIVE_TESTS=1 uv run pytest -m live
```

Use the preview server for interactive UI work instead of launching repeated native windows:

```bash
uv run python scripts/ui_preview.py --port 8765 --data-dir /tmp/expedite-ui-preview
```

## Implementation conventions

- Keep lines at or below 100 characters and satisfy the Ruff rules in `ruff.toml`.
- Add type annotations to new functions and preserve the existing concise docstring style.
- Keep page modules focused on UI behavior. Put persistence in repositories/storage modules and reusable business rules in domain modules.
- Use repository transactions for multi-step database writes. Preserve SQLite foreign-key enforcement and per-event order numbering.
- Keep the core order flow offline. Theme assets and fonts must remain locally packaged.
- Preserve accessible control names and labels. Browserless UI tests locate several controls by visible text or `aria-label`.
- Update tests when behavior changes. Prefer tests of user-visible behavior or persistence outcomes over assertions tied to implementation details.
- Platform-specific printing code must remain importable and testable on non-Windows hosts; mock the Windows spooler boundary in tests.
- When adding packaged files, update both PyInstaller specs and relevant license documentation.

## Data safety

The default data directory may resolve to the user's Documents directory and contains the application SQLite database plus generated exports and labels. Never run development checks against that location.

- Set `EVENT_INTAKE_DATA_DIR` to a disposable directory for manual or scripted testing.
- Use pytest's `tmp_path` and reset the cached database engine with `dispose_engine()` when changing the configured data directory in-process.
- Do not modify or commit realistic files under `data/`. Copy any useful production-like database to a temporary directory first.
- Keep browser profiles, screenshots, logs, and generated test artifacts in a temporary directory and clean up spawned preview/browser processes.

## UI and native-app checks

Browserless NiceGUI tests cover Python-side page interactions. Use the live harness for browser behavior such as focus, scrolling, CSS layout, handshake timing, and print-lock regressions. Reserve native mode for deliberate pywebview or packaged-app smoke tests, and clean up its full process tree afterward.

For visual changes, check representative narrow and desktop widths and verify DOM state or computed layout in addition to screenshots. Avoid fixed sleeps where an observable UI or persistence condition can be polled.

## Packaging

Use incremental PyInstaller builds for local iteration. Use `--clean` for releases or after changes to Python, dependencies, hooks, or spec files. Windows artifacts are built and smoke-tested through `.github/workflows/windows-build.yml`; PyInstaller cannot cross-compile the Windows application from macOS.

Do not edit generated content in `dist/`, PyInstaller work directories, caches, or `__pycache__` folders.
