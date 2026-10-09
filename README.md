# Expedite

An offline-first desktop app for event order intake, with a Windows-classic interface,
local data storage, and thermal receipts. Windows is the primary deployment target.

## Install

Download the Windows installer from [Releases](https://github.com/johnmyrda/expedite/releases),
run it, and launch Expedite from the Start Menu. Installation requires no administrator access.
The unsigned installer may trigger a Windows SmartScreen warning.

## Use the app

1. Create or open an event on the Events page.
2. Enter customer details and line items on **Intake**, then submit the order.
3. Use **Orders** to review, edit, export, or reprint saved orders.

Use **Tools > Catalog** to manage reusable items. Star up to 10 active items to include them
in Intake's Quick Add group. Set event-specific prices on the **Management** tab.

Use **Tools > Receipt Settings...** to change the receipt name, upload a PNG logo (up to 5 MB),
and adjust the blank Notes area (0–200 mm; default 60 mm).

## Printing

Windows automatically prints receipts when orders are submitted or updated. Use the Print
buttons to retry or reprint; orders remain saved if printing fails. On other platforms,
receipt PNGs are generated but direct printing is unavailable.

Receipts target the Rongta RP332 80 mm thermal printer. The configured printer must support
ESC/POS raster commands and defaults to `RONGTA 80mm Series Printer`. To use another installed
printer, run this in PowerShell and restart Expedite:

```powershell
[Environment]::SetEnvironmentVariable(
    "EXPEDITE_PRINTER_NAME", "Exact Windows printer name", "User"
)
```

## Data and backups

Data is stored in `Expedite` under your Documents folder when available. Use
**File > Open Data Folder** to find it. Set `EVENT_INTAKE_DATA_DIR` to override the location.

Close the app before copying `expedite.sqlite3` for backup. It contains events, catalog,
pricing, orders, and receipt settings, including the logo. Copy the entire data folder to
retain generated receipt PNGs and CSV exports too. Restoring the database alone recreates
missing event folders, but not previously generated files.

## Startup problems

On Windows, run `Run Expedite Diagnostics.cmd` from the application folder, or launch
`Expedite.exe --diagnostic`. Share the error and log at:

```text
%LOCALAPPDATA%\Expedite\logs\expedite-diagnostic.log
```

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for setup, testing, builds, and releases.
