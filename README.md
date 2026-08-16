# Expedite

Desktop app for event order intake, CSV export, and 4x6 label image generation.

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

Build a local macOS app with PyInstaller:

```bash
uv run pyinstaller --noconfirm --clean --workpath build/pyinstaller --distpath dist build/expedite.spec
```

On macOS, launch `dist/Expedite.app` to avoid opening a Terminal window.

Build a local Windows EXE on Windows:

```powershell
uv run pyinstaller --noconfirm --clean --workpath build/pyinstaller --distpath dist build/expedite-windows.spec
```

The Windows output is written to `dist/Expedite.exe`.

## v1 Scope

- Fixed fields: Name, Phone, Work Request, Cost
- Non-blocking validation warnings
- Sequential per-event order IDs
- Appends each order to `orders.csv`
- Saves 4x6 PNG labels under each event's `labels/` folder
- No in-app printing or automated cross-platform build workflow
