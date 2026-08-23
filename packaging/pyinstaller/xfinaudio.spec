# -*- mode: python ; coding: utf-8 -*-

import os
import re
import subprocess
import tomllib
from pathlib import Path

project_root = Path(SPECPATH).parents[1]
ffmpeg_binary = project_root / "packaging" / "ffmpeg" / "ffmpeg"


def _ffmpeg_probe(command: tuple[str, ...]) -> str:
    result = subprocess.run(
        command, stdin=subprocess.DEVNULL, capture_output=True, text=True, shell=False, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"Bundled FFmpeg validation failed: {' '.join(command)}")
    return result.stdout or ""


def validate_ffmpeg_bundle(binary: Path) -> Path:
    """Fail packaging before including an invalid universal2 ebur128 executable."""
    binary = binary.resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise RuntimeError(f"Bundled FFmpeg is missing or not executable: {binary}")
    _ffmpeg_probe(("lipo", "-verify_arch", "arm64", "x86_64", str(binary)))
    version = _ffmpeg_probe((str(binary), "-version"))
    if re.search(r"\bffmpeg version 7\.1\.1(?:\s|$)", version) is None:
        raise RuntimeError("Bundled FFmpeg is not the required 7.1.1 builder version")
    filters = _ffmpeg_probe((str(binary), "-hide_banner", "-filters"))
    if re.search(r"\bebur128\b", filters) is None:
        raise RuntimeError("Bundled FFmpeg lacks ebur128")
    filter_help = _ffmpeg_probe((str(binary), "-hide_banner", "-h", "filter=ebur128"))
    if re.search(r"\bpeak\b.*\btrue\b|\btrue\b.*\bpeak\b", filter_help.lower()) is None:
        raise RuntimeError("Bundled FFmpeg lacks ebur128 true-peak support")
    return binary


bundled_ffmpeg = validate_ffmpeg_bundle(ffmpeg_binary)

# Without this the bundle reports CFBundleShortVersionString 0.0.0, which is
# what macOS shows in Get Info and what every crash report carries -- making
# builds indistinguishable exactly when you need to tell them apart.
app_version = tomllib.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]

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
    binaries=[(str(bundled_ffmpeg), ".")],
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
    upx_exclude=["ffmpeg"],
    name="XfinAudio",
)

icon_path = project_root / "assets" / "icons" / "app-icon.icns"
app = BUNDLE(
    coll,
    name="XfinAudio.app",
    icon=str(icon_path) if icon_path.exists() else None,
    bundle_identifier="com.bluesystemio.xfinaudio",
    version=app_version,
)
