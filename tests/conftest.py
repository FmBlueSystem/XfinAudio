import os

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication instance for Qt widget tests."""
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    return QApplication([])


@pytest.fixture(autouse=True)
def _disable_spectral_completion_worker(monkeypatch):
    """Prevent background spectral workers from leaking QThreads in widget tests."""
    from xfinaudio.desktop import main_window as mw_module

    if hasattr(mw_module, "MainWindow"):
        monkeypatch.setattr(
            mw_module.MainWindow,
            "_start_spectral_completion_worker",
            lambda self, records: None,
        )


@pytest.fixture(autouse=True, scope="session")
def _no_root_build_artifacts():
    """Prevent accidental test runs from a dirty checkout with build/ or dist/ present."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    assert not (root / "build").exists(), f"Remove {root / 'build'} before running tests"
    assert not (root / "dist").exists(), f"Remove {root / 'dist'} before running tests"
