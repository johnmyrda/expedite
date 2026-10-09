# Developing Expedite

Expedite uses Python 3.11+, NiceGUI/pywebview, SQLModel/SQLite, Pillow, and PyInstaller.
Application usage is documented in [README.md](README.md); coding conventions and the repository
map are in [AGENTS.md](AGENTS.md).

## Setup and run

Install [uv](https://docs.astral.sh/uv/), then run:

```bash
uv sync --locked
```

**Use disposable data for development, never the default application data folder.** Before
launching the native app, set `EVENT_INTAKE_DATA_DIR` to a test directory:

```bash
# macOS/Linux
EVENT_INTAKE_DATA_DIR=/tmp/expedite-dev uv run expedite
```

```powershell
# Windows
$env:EVENT_INTAKE_DATA_DIR = Join-Path $env:TEMP "expedite-dev"
uv run expedite
```

For routine UI work, prefer the browser-only preview. It runs the real pages without opening
native windows; supply a disposable path appropriate for your platform:

```bash
uv run python scripts/ui_preview.py --port 8765 --data-dir /tmp/expedite-preview
```

## Checks

[Poe the Poet](https://poethepoet.natn.io/) is included in the development dependencies.
Its command tasks work without Make or Bash on Windows.

```bash
uv run poe --help       # list tasks
uv run poe check        # lint, types, and tests
uv run poe test -q      # individual tasks: lint, types, test
uv run pytest tests/test_validation.py  # focused test
```

Live browser checks require Chrome or Chromium and manage their own disposable data:

```bash
uv run python scripts/live_ui_harness.py
```

Set `CHROME_PATH` if needed. See [LIVE_TESTING.md](LIVE_TESTING.md) for harness options and
browser/native testing guidance.

## Build

Build on the target OS; PyInstaller cannot cross-compile Windows artifacts from macOS.

| Platform | Command | Output |
| --- | --- | --- |
| macOS | `uv run poe build-mac` | `dist/Expedite.app` |
| Windows | `uv run poe build-windows` | `dist/Expedite/` |

Builds are incremental by default. Append `--clean` for releases or after changing Python,
dependencies, hooks, or spec files. The specs in `build/` include the application icons and
offline theme assets; do not edit generated files in `dist/` or `build/pyinstaller/`.

To create a Windows installer, install Inno Setup 6, build the Windows app, then run PowerShell
with an `AppVersion` matching `pyproject.toml`:

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" `
  "/DAppVersion=0.1.0" "build/windows/expedite.iss"
```

Output: `dist/installer/Expedite-0.1.0-Windows-Setup.exe`.

## CI and releases

**Build Windows** runs on pull requests and can be started manually in GitHub Actions.
It checks the code, builds the app and installer, then installs, verifies interactive native
startup, and uninstalls a test copy. Artifacts:

- `expedite-windows-installer`: user-facing installer
- `expedite-windows`: unpacked diagnostic build
- `expedite-windows-diagnostics`: smoke-test logs, including on failure

Before releasing, align the project version and tag, run a clean build, and test the installer
with disposable data through order entry, receipts, printing where hardware is available,
File > Exit, and uninstall. CI's startup check does not cover that full workflow.

Run **Release Windows** manually from the intended commit with a new matching tag such as
`v0.1.0`. It reuses the build/smoke checks and publishes the installer only if they pass.
Workflow definitions are in [.github/workflows](.github/workflows).

## Theme assets

The interface vendors [98.css](https://jdan.github.io/98.css/) with a NiceGUI/Quasar compatibility
layer. It prefers system Tahoma and bundles Wine Tahoma fallbacks; all assets work offline.
The theme and font licenses are in [src/expedite/static](src/expedite/static).
