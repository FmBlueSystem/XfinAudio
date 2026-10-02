"""Locate bundled desktop assets without depending on the working directory."""

from __future__ import annotations

import sys
from pathlib import Path


def asset_path(*parts: str) -> Path:
    """Resolve PyInstaller, installed-wheel or source-tree asset paths."""
    package_root = Path(__file__).resolve().parents[1]
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "assets" / Path(*parts)
    installed = package_root / "assets"
    if installed.is_dir():
        return installed.joinpath(*parts)
    return package_root.parents[1] / "assets" / Path(*parts)
