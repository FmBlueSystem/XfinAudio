from importlib import metadata
from pathlib import Path
from unittest.mock import Mock

from xfinaudio.desktop.menu import Menu


def test_about_displays_installed_package_version(monkeypatch):
    resolve = Mock(return_value="2.1.0")
    monkeypatch.setattr(metadata, "version", resolve)
    about = Mock()
    monkeypatch.setattr("xfinaudio.desktop.menu.QMessageBox.about", about)
    Menu(Mock(tr=lambda text: text)).show_about_dialog()
    assert "Version 2.1.0" in about.call_args.args[2]
    assert "Version 1.0" not in about.call_args.args[2]
    resolve.assert_called_once_with("xfinaudio")


def test_about_missing_metadata_does_not_claim_a_stale_version(monkeypatch):
    monkeypatch.setattr(metadata, "version", Mock(side_effect=metadata.PackageNotFoundError))
    about = Mock()
    monkeypatch.setattr("xfinaudio.desktop.menu.QMessageBox.about", about)
    Menu(Mock(tr=lambda text: text)).show_about_dialog()
    assert "Version Unknown" in about.call_args.args[2]
    assert "Version 1.0" not in about.call_args.args[2]


def test_frozen_app_includes_own_distribution_metadata():
    spec = (Path(__file__).resolve().parents[1] / "packaging/pyinstaller/xfinaudio.spec").read_text()
    assert "from PyInstaller.utils.hooks import copy_metadata" in spec
    assert 'datas=assets + copy_metadata("xfinaudio")' in spec


def test_compiled_spanish_about_uses_current_version_template(qapp, monkeypatch):
    from PySide6.QtCore import QTranslator

    translator = QTranslator()
    catalog = Path(__file__).resolve().parents[1] / "assets/translations/xfinaudio_es.qm"
    assert translator.load(str(catalog))
    monkeypatch.setattr(metadata, "version", Mock(return_value="2.1.0"))
    about = Mock()
    monkeypatch.setattr("xfinaudio.desktop.menu.QMessageBox.about", about)
    host = Mock(tr=lambda text: translator.translate("MainWindow", text) or text)
    Menu(host).show_about_dialog()
    assert "Versión 2.1.0" in about.call_args.args[2]
