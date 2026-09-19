# -*- mode: python ; coding: utf-8 -*-
"""Windows PyInstaller spec for Expedite."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
project_root = Path(SPECPATH).parent

nicegui_datas = collect_data_files("nicegui")
webview_datas = collect_data_files("webview")
# The PyInstaller pythonnet hook only collects Python.Runtime.dll. Pythonnet 3.1
# also requires the managed assemblies and dependency metadata beside that DLL.
pythonnet_runtime_datas = collect_data_files(
    "pythonnet",
    subdir="runtime",
    excludes=["**/Python.Runtime.dll"],
)

nicegui_hidden_imports = collect_submodules(
    "nicegui",
    filter=lambda name: not name.startswith("nicegui.testing"),
)
webview_hidden_imports = collect_submodules(
    "webview",
    filter=lambda name: name != "webview.platforms.android",
)

a = Analysis(
    [str(project_root / "src" / "expedite" / "main.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=nicegui_datas + webview_datas + pythonnet_runtime_datas,
    hiddenimports=nicegui_hidden_imports + webview_hidden_imports + ["win32print", "pywintypes"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Expedite",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=None,
)

collection = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Expedite",
)
