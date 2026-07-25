import contextlib
import os

# Before PySide6 is imported, not after: Qt has to learn it is headless while
# it still matters. Twice the CI job burned its full 20-minute timeout inside
# `uv run pytest` having emitted nothing at all -- no progress dot, no
# collection error -- on a runner where nothing set this and the announcement
# came one line too late.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


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


@pytest.fixture(autouse=True)
def _release_audio_players(monkeypatch):
    """Release every AudioPlayer a test creates.

    QMediaPlayer keeps an ffmpeg decode thread alive for as long as a source is
    attached, so a player left behind outlives its test. The v1.0.2 publish run
    segfaulted at 83% of the suite with ffmpeg still printing "Duration:" while
    Python was tearing down, and later runs hung to the 20-minute job timeout
    with an orphan process at cleanup. Roughly twenty players were created
    across the suite and none of them released its decoder.

    Patching the constructor keeps the registry out of production code; the
    players themselves only need the `shutdown()` they should have had anyway.
    """
    from xfinaudio.desktop.audio_player import AudioPlayer

    created: list[AudioPlayer] = []
    original_init = AudioPlayer.__init__

    def _tracking_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        created.append(self)

    monkeypatch.setattr(AudioPlayer, "__init__", _tracking_init)
    yield
    for player in created:
        # The C++ side may already be gone when a parented player's owner was
        # destroyed during the test.
        with contextlib.suppress(RuntimeError):
            player.shutdown()


@pytest.fixture(autouse=True, scope="session")
def _no_root_build_artifacts():
    """Prevent accidental test runs from a dirty checkout with build/ or dist/ present."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    assert not (root / "build").exists(), f"Remove {root / 'build'} before running tests"
    assert not (root / "dist").exists(), f"Remove {root / 'dist'} before running tests"
