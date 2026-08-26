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

The `Build Windows` workflow uses a GitHub-hosted Windows runner, executes all quality
checks, creates the onedir application, and uploads it as the `expedite-windows` artifact.

To create a build manually:

1. Open the repository's **Actions** tab on GitHub.
2. Select **Build Windows**.
3. Choose **Run workflow**.
4. Download `expedite-windows` from the completed run's **Artifacts** section.

After downloading, keep all artifact files together and launch `Expedite.exe`.

The workflow also supports `workflow_call`, so a future CI or release workflow can reuse it
as a job:

```yaml
jobs:
  windows-build:
    uses: ./.github/workflows/windows-build.yml
```

## v1 Scope

- Fixed fields: Name, Phone, Work Request, Cost
- Non-blocking validation warnings
- Sequential per-event order IDs
- Stores event and order data in the application SQLite database
- Saves Rongta RP332-targeted thermal receipt-label PNGs under each event's `labels/` folder
- No in-app printing or automated cross-platform build workflow
