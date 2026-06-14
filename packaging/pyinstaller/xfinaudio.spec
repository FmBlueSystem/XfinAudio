# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH).parents[1]

block_cipher = None

# Collect assets (icons + translations) so the frozen app can resolve them at runtime.
asset_dir = project_root / "assets"
assets = []
if asset_dir.exists():
    for subpath in asset_dir.rglob("*"):
        if subpath.is_file():
            rel = subpath.relative_to(project_root)
            assets.append((str(subpath), str(rel.parent)))

analysis = Analysis(
    [str(project_root / "src/xfinaudio/desktop/app.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=assets,
    hiddenimports=[
        "pydantic",
        "pydantic.v1",
        "mutagen",
        "mutagen.mp3",
        "mutagen.flac",
        "mutagen.m4a",
        "mutagen.wave",
        "mutagen.aiff",
        "mutagen.ogg",
        "mutagen.oggvorbis",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtMultimedia",
        "setproctitle",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="XfinAudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="XfinAudio",
)

icon_path = project_root / "assets" / "icons" / "app-icon.icns"
app = BUNDLE(
    coll,
    name="XfinAudio.app",
    icon=str(icon_path) if icon_path.exists() else None,
    bundle_identifier="com.bluesystemio.xfinaudio",
)
