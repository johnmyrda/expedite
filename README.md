# Expedite

Desktop app for event order intake, SQLite-backed storage, and thermal receipt-label image generation.

## Development

This project uses [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
uv run expedite
```

Event data defaults to the user's Documents folder when available. Override with:

```bash
EVENT_INTAKE_DATA_DIR=/path/to/events uv run expedite
```

The application database is `expedite.sqlite3` in that directory. Copying this file is sufficient
to restore events, catalog data, pricing, orders, and order lines on another machine. Expedite
recreates missing event folders and their `labels/` subdirectories from database metadata when
events are listed or opened. Previously generated CSV and PNG files remain separate filesystem
artifacts.

## Interface theme

The desktop interface uses a locally vendored copy of
[98.css](https://jdan.github.io/98.css/) with a NiceGUI/Quasar compatibility layer for clear,
high-contrast controls and the bundled Pixelated MS Sans Serif font. Pages fill the native
application viewport without simulating an additional desktop window or title bar. Theme assets are
packaged with the
application and do not require internet access. The upstream MIT license is included at
`src/expedite/static/98.css.LICENSE`.

## Catalog favorites

Use the star buttons on the Catalog page to favorite up to 10 active items. Favorites appear as
clickable chips on each event's intake page. Hover over a chip to see the item's description and
its effective event price; click it to add the item to the order.

## Printing

On Windows, submitting or updating an order sends its generated label directly to the configured
ESC/POS printer. Print icon buttons beside label-open buttons support manual reprints. Orders stay
saved if printing fails, and Expedite displays an error that can be retried with the print button.

The configured Windows printer name defaults to `RONGTA 80mm Series Printer`. To use a different installed
printer name, set a persistent user environment variable and restart Expedite:

```powershell
[Environment]::SetEnvironmentVariable(
    "EXPEDITE_PRINTER_NAME",
    "Exact Windows printer name",
    "User"
)
```

Automatic printing is currently Windows-only. The printer must support ESC/POS raster commands.
Receipts leave zero-dollar Cost values blank, include an empty Paid checkbox, and provide a blank
Notes area. The Notes area defaults to 60 mm. Use the settings button on the Events page to change
its height from 0 to 200 mm, customize the receipt name, and upload or remove a PNG logo up to 5 MB.
Logos are scaled to fit the receipt while preserving their aspect ratio. These application-wide
branding settings are stored in SQLite, travel with database backups, and apply to newly generated
receipts. `EXPEDITE_LABEL_NOTES_HEIGHT_MM` can override the initial Notes default before a value has
been saved in the UI.

## Packaging

PyInstaller can reuse the analysis and package caches under `build/pyinstaller`. For fast
local iteration, keep that directory and do not pass `--clean`:

```bash
uv run pyinstaller --noconfirm --workpath build/pyinstaller --distpath dist build/expedite.spec
```

The macOS onedir build is written to `dist/Expedite.app`.

Use the equivalent incremental command on Windows:

```powershell
uv run pyinstaller --noconfirm --workpath build/pyinstaller --distpath dist build/expedite-windows.spec
```

The Windows onedir build is written to `dist/Expedite/`. It is the input to the Inno Setup
installer and remains available as a diagnostic artifact. After building it, create a per-user
installer with Inno Setup 6:

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" `
  "/DAppVersion=0.1.0" `
  "build/windows/expedite.iss"
```

The installer is written to `dist/installer/Expedite-0.1.0-Windows-Setup.exe`. It installs under
`%LOCALAPPDATA%\Programs\Expedite`, creates a Start Menu shortcut, offers an optional desktop
shortcut, and requires no administrator access.

Run a clean build before producing a release, or after changing Python, dependencies,
PyInstaller hooks, or the spec file:

```bash
uv run pyinstaller --noconfirm --clean --workpath build/pyinstaller --distpath dist build/expedite.spec
```

```powershell
uv run pyinstaller --noconfirm --clean --workpath build/pyinstaller --distpath dist build/expedite-windows.spec
```

### Building Windows on GitHub Actions

The `Build Windows` workflow uses a GitHub-hosted Windows runner, executes all quality checks,
creates the onedir application and Inno Setup installer, and uploads both as 14-day artifacts:

- `expedite-windows-installer`: the user-facing per-user installer
- `expedite-windows`: the unpacked diagnostic build

It runs automatically whenever a pull request is opened or updated. It requires no release tag
and can also be run manually or reused by future CI workflows. Its optional manual/reusable
`version` input defaults to the project version in `pyproject.toml`.

To create a test build manually:

1. Open the repository's **Actions** tab on GitHub.
2. Select **Build Windows**.
3. Choose **Run workflow**.
4. Download `expedite-windows-installer` from the completed run's **Artifacts** section.

The build workflow verifies that every pythonnet runtime dependency was packaged, silently installs
the generated installer into a temporary per-user directory, launches that installed executable,
requests its home page, and requires pywebview to emit the native window's `shown` event. It then
uninstalls the test copy. Smoke-test logs are uploaded as the `expedite-windows-diagnostics`
artifact, including when the test fails.

The separate `Release Windows` workflow remains manual. It requires a tag, calls the same build and
smoke-test workflow, and only publishes a release when they pass. To create a release, select
**Release Windows**, enter a new tag such as `v0.1.0`, and run the workflow. The resulting release
contains `Expedite-<version>-Windows-Setup.exe`.

The tag must match `vMAJOR.MINOR.PATCH`, optionally followed by a suffix such as `-rc.1`. The
workflow creates the tag at the selected commit, generates release notes, and fails rather than
replacing an existing release.

Download and run the installer, then launch Expedite from the Start Menu. Because the installer
writes the application payload itself, its managed DLLs do not inherit the downloaded file's
Internet-origin marker. The unsigned installer may still trigger a one-time Windows SmartScreen
warning until release signing is added.

#### Windows diagnostics

Every Windows build includes `Run Expedite.cmd` and `Run Expedite Diagnostics.cmd`. Both remove
Windows' Internet-origin marker from the extracted application files before launching. The
diagnostic launcher then starts the same production executable with diagnostic mode enabled; there
is no separate build whose behavior could differ. Diagnostic mode attaches or creates a console
and records startup output and uncaught tracebacks at:

```text
%LOCALAPPDATA%\Expedite\logs\expedite-diagnostic.log
```

The same mode can be added to a Windows shortcut by setting its target to:

```text
"C:\path\to\Expedite\Expedite.exe" --diagnostic
```

If normal startup fails, run the diagnostic launcher and share the displayed error and log file.

The build workflow supports `workflow_call`, so future CI can request a build without release
permissions:

```yaml
jobs:
  windows-build:
    uses: ./.github/workflows/windows-build.yml
```

The release workflow intentionally supports manual dispatch only.

## v1 Scope

- Fixed fields: Name, Phone, Work Request, Cost
- Non-blocking validation warnings
- Sequential per-event order IDs
- Stores event and order data in the application SQLite database
- Saves Rongta RP332-targeted thermal receipt-label PNGs under each event's `labels/` folder
- No in-app printing or automated cross-platform build workflow
