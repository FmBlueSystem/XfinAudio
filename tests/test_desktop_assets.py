"""Runtime assets resolve consistently in source, wheel and frozen layouts."""

import sys
import tomllib
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from xfinaudio.desktop import i18n


def test_real_spanish_catalog_loads_from_source(qapp: QApplication) -> None:
    try:
        assert i18n.translations_dir().joinpath("xfinaudio_es.qm").is_file()
        assert i18n.install_translator("es_ES") is not None
        assert QCoreApplication.translate("BuildViewModel", "Consistent Loudness") == "Sonoridad consistente"
    finally:
        i18n.remove_translator()


@pytest.mark.parametrize("layout", ["source", "installed", "frozen"])
def test_asset_resolver_matches_runtime_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, layout: str) -> None:
    from xfinaudio.desktop import assets

    source = tmp_path / "repo" / "src" / "xfinaudio" / "desktop" / "assets.py"
    installed = tmp_path / "site-packages" / "xfinaudio" / "desktop" / "assets.py"
    module_path = source if layout == "source" else installed
    root = {
        "source": tmp_path / "repo" / "assets",
        "installed": installed.parents[1] / "assets",
        "frozen": tmp_path / "bundle" / "assets",
    }[layout]
    icon = root / "icons" / "app-icon-512x512.png"
    icon.parent.mkdir(parents=True)
    icon.write_bytes(b"synthetic asset")
    monkeypatch.setattr(assets, "__file__", str(module_path))
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    monkeypatch.setattr(sys, "frozen", layout == "frozen", raising=False)

    assert assets.asset_path("icons", "app-icon-512x512.png") == icon


def test_wheel_declares_runtime_assets() -> None:
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / "pyproject.toml").read_text())
    included = config["tool"]["hatch"]["build"]["targets"]["wheel"].get("force-include", {})
    assert included == {
        "assets/icons": "xfinaudio/assets/icons",
        "assets/translations": "xfinaudio/assets/translations",
    }
