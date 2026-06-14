"""Tests that XfinAudio preserves user data across app updates."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.config.settings import AppSettings, ExportSettings, LibrarySettings
from xfinaudio.config.settings_repository import SettingsRepository
from xfinaudio.desktop.app import default_database_path, default_settings_path
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanProgress
from xfinaudio.library.track_repository import TrackRepository


def ensure_app():
    from PySide6.QtWidgets import QApplication

    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    return QApplication([])


class FakeScanService:
    def __init__(self) -> None:
        self.scanned_folder: Path | None = None

    def scan(self, folder: Path, **kwargs):
        self.scanned_folder = folder
        progress_callback = kwargs.get("on_progress")
        if progress_callback is not None:
            progress_callback(ScanProgress(processed_count=1, total_count=1, current_path=folder / "track.flac"))
        return [
            TrackRecord(
                path=str(folder / "track.flac"),
                title="Track One",
                artist="Artist One",
                bpm=116.0,
                camelot_key="11B",
                energy_level=5,
                metadata_status="complete",
            ),
        ]


class FakeRepository:
    def __init__(self) -> None:
        self.saved_records: list[TrackRecord] = []

    def save_scan_results(self, records: list[TrackRecord]) -> None:
        self.saved_records = records


def test_default_app_owned_paths_are_under_home_dot_directory() -> None:
    db_path = default_database_path()
    settings_path = default_settings_path()

    assert db_path.name == "xfinaudio.sqlite3"
    assert db_path.parent.name == ".xfinaudio"
    assert settings_path.name == "settings.json"
    assert settings_path.parent.name == ".xfinaudio"


def test_settings_repository_preserves_existing_settings_across_loads(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    repository = SettingsRepository(settings_path)
    original = AppSettings(
        library=LibrarySettings(last_scan_folder=tmp_path / "music"),
        export=ExportSettings(safe_export_folder=tmp_path / "exports"),
    )
    repository.save(original)

    # Simulate a new app version opening the same file.
    new_repository = SettingsRepository(settings_path)
    loaded = new_repository.load()

    assert loaded.library.last_scan_folder == original.library.last_scan_folder
    assert loaded.export.safe_export_folder == original.export.safe_export_folder


def test_track_repository_preserves_existing_records_across_opens(tmp_path: Path) -> None:
    db_path = tmp_path / "xfinaudio.sqlite3"
    first_repository = TrackRepository(db_path)
    original = TrackRecord(
        path="/music/track.flac",
        title="Track One",
        artist="Artist One",
        bpm=116.0,
        camelot_key="11B",
        energy_level=5,
        metadata_status="complete",
    )
    first_repository.save_scan_results([original])

    # Simulate a new app version opening the same database.
    second_repository = TrackRepository(db_path)
    loaded = second_repository.list_tracks()

    assert loaded == [original]


def test_main_window_with_defaults_loads_existing_settings_and_tracks(tmp_path: Path) -> None:
    ensure_app()
    db_path = tmp_path / "xfinaudio.sqlite3"
    settings_path = tmp_path / "settings.json"

    # Pre-populate data as if from a previous version.
    track_repository = TrackRepository(db_path)
    record = TrackRecord(
        path=str(tmp_path / "track.flac"),
        title="Track One",
        bpm=120.0,
        camelot_key="8A",
        energy_level=5,
        metadata_status="complete",
    )
    track_repository.save_scan_results([record])

    settings_repository = SettingsRepository(settings_path)
    settings_repository.save(
        AppSettings(library=LibrarySettings(last_scan_folder=tmp_path / "music")),
    )

    window = MainWindow.with_defaults(db_path, settings_path)

    assert window.settings.library.last_scan_folder == tmp_path / "music"
    assert any(r.path == record.path for r in window.scanned_records)
