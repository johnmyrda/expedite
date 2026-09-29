# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Expedite."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
project_root = Path(SPECPATH).parent

nicegui_datas = collect_data_files("nicegui")
webview_datas = collect_data_files("webview")
expedite_static_datas = [
    (str(project_root / "src" / "expedite" / "static"), "expedite/static"),
]

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
    datas=nicegui_datas + webview_datas + expedite_static_datas,
    hiddenimports=nicegui_hidden_imports + webview_hidden_imports,
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
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

collection = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Expedite",
)

app = BUNDLE(
    collection,
    name="Expedite.app",
    icon=None,
    bundle_identifier="com.johnmyrda.expedite",
    info_plist={
        "CFBundleName": "Expedite",
        "CFBundleDisplayName": "Expedite",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "NSHighResolutionCapable": True,
    },
)
