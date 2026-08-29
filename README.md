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

The Windows onedir build is written to `dist/Expedite/`. Launch
`dist/Expedite/Expedite.exe`, and keep the complete directory together when installing or
copying the application.

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
creates the onedir application, and uploads the unpacked build as the 14-day
`expedite-windows` artifact. It requires no release tag and can be run freely for CI and testing.

To create a test build manually:

1. Open the repository's **Actions** tab on GitHub.
2. Select **Build Windows**.
3. Choose **Run workflow**.
4. Download `expedite-windows` from the completed run's **Artifacts** section.

The build workflow launches the packaged executable on Windows, requests its home page, and
verifies that the NiceGUI native-window process remains alive. Smoke-test logs are uploaded as the
`expedite-windows-diagnostics` artifact, including when the test fails.

The separate `Release Windows` workflow requires a tag, calls the same build and smoke-test
workflow, and only publishes a release when they pass. To create a release, select
**Release Windows**, enter a new tag such as `v0.1.0`, and run the workflow. The resulting release
contains `Expedite-<tag>-windows.zip`.

The tag must match `vMAJOR.MINOR.PATCH`, optionally followed by a suffix such as `-rc.1`. The
workflow creates the tag at the selected commit, generates release notes, and fails rather than
replacing an existing release.

After extracting either download, keep the complete `Expedite` directory together and launch
`Expedite.exe`.

#### Windows diagnostics

Every Windows build includes `Run Expedite Diagnostics.cmd`. It launches the same production
executable with diagnostic mode enabled; there is no separate build whose behavior could differ.
Diagnostic mode attaches or creates a console and records startup output and uncaught tracebacks at:

```text
%LOCALAPPDATA%\Expedite\logs\expedite-diagnostic.log
```

The same mode can be added to a Windows shortcut by setting its target to:

```text
"C:\path\to\Expedite\Expedite.exe" --diagnostic
```

If normal startup fails, run the diagnostic launcher and share the displayed error and log file.

Both workflows support `workflow_call`. Future CI can request a build without release permissions:

```yaml
jobs:
  windows-build:
    uses: ./.github/workflows/windows-build.yml
```

A release caller supplies a tag and grants write access to repository contents:

```yaml
jobs:
  windows-release:
    permissions:
      contents: write
    uses: ./.github/workflows/windows-release.yml
    with:
      tag: v0.1.0
```

## v1 Scope

- Fixed fields: Name, Phone, Work Request, Cost
- Non-blocking validation warnings
- Sequential per-event order IDs
- Stores event and order data in the application SQLite database
- Saves Rongta RP332-targeted thermal receipt-label PNGs under each event's `labels/` folder
- No in-app printing or automated cross-platform build workflow
