from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtGui import QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QListWidget,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
)

from xfinaudio.audio.spectral_profile import CURRENT_ANALYSIS_VERSION, SpectralProfile
from xfinaudio.config.settings import AppSettings, ExportSettings, LibrarySettings, WindowSettings
from xfinaudio.desktop import export_coordinator, main_window
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.exporting.explainability import PlaylistExplanation, TrackExplanation, TransitionExplanation
from xfinaudio.exporting.serato_crate import parse_serato_crate_bytes
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancelledError, ScanProgress
from xfinaudio.quality.dj_readiness import DjReadinessCheck, DjReadinessReport
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import recommend_playlist


def ensure_app() -> QApplication:
    existing_app = QApplication.instance()
    if isinstance(existing_app, QApplication):
        return existing_app
    return QApplication([])


class FakeScanService:
    def __init__(self) -> None:
        self.scanned_folder: Path | None = None

    def scan(self, folder: Path, **kwargs) -> list[TrackRecord]:
        self.scanned_folder = folder
        progress_callback = kwargs.get("on_progress")
        if progress_callback is not None:
            progress_callback(ScanProgress(processed_count=1, total_count=2, current_path=folder / "track.flac"))
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
            TrackRecord(path=str(folder / "partial.aif"), title="Partial", metadata_status="incomplete"),
        ]


class FakeRepository:
    def __init__(self) -> None:
        self.saved_records: list[TrackRecord] = []

    def save_scan_results(self, records: list[TrackRecord]) -> None:
        self.saved_records = records


class FakeSettingsRepository:
    def __init__(self) -> None:
        self.saved_settings: AppSettings | None = None

    def load(self) -> AppSettings:
        return self.saved_settings or AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.saved_settings = settings


class RefreshingScanService:
    def __init__(self, records: list[TrackRecord]) -> None:
        self.records = records
        self.scanned_folder: Path | None = None

    def scan(self, folder: Path, **kwargs) -> list[TrackRecord]:
        self.scanned_folder = folder
        progress_callback = kwargs.get("on_progress")
        if progress_callback is not None:
            progress_callback(
                ScanProgress(
                    processed_count=len(self.records),
                    total_count=len(self.records),
                    current_path=folder,
                )
            )
        return self.records


def make_recommendation(records: list[TrackRecord]):
    return recommend_playlist(records, "build")


def _visible_track_titles(window: MainWindow) -> list[str]:
    return [
        _table_item_text(_library_tracks_table(window), row, 0)
        for row in range(_library_tracks_table(window).rowCount())
        if not _library_tracks_table(window).isRowHidden(row)
    ]


def _table_item(table: QTableWidget, row: int, column: int) -> QTableWidgetItem:
    item = table.item(row, column)
    assert item is not None
    return item


def _table_item_text(table: QTableWidget, row: int, column: int) -> str:
    return _table_item(table, row, column).text()


def _header_text(table: QTableWidget, column: int) -> str:
    item = table.horizontalHeaderItem(column)
    assert item is not None
    return item.text()


def _table_headers(table: QTableWidget) -> list[str]:
    return [_header_text(table, column) for column in range(table.columnCount())]


def _library_tracks_table(window: MainWindow) -> QTableWidget:
    return window._library_screen.tracks_table


def _shortcut_text(window: MainWindow, name: str) -> str:
    return window._keyboard_shortcuts[name].key().toString(QKeySequence.SequenceFormat.PortableText)


def _track_table_headers(window: MainWindow) -> list[str]:
    return _table_headers(_library_tracks_table(window))


def test_main_window_does_not_create_dead_tracks_table() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert not hasattr(window, "tracks_table")
    assert _library_tracks_table(window).columnCount() == 12


def test_main_window_constructs_desktop_scanning_skeleton() -> None:
    app = ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window.windowTitle() == "XfinAudio"
    assert window._library_screen.folder_button.text() == "Choose Folder"
    assert window._library_screen.scan_button.text() == "Scan Metadata"
    assert window._build_screen.strategy_combo.count() == 10
    assert window._build_screen.recommend_button.text() == "Recommend Playlist"
    assert _library_tracks_table(window).columnCount() >= 7
    assert window._review_screen.recommendation_table.columnCount() >= 6
    assert app is not None


def test_main_window_constructor_exposes_initial_panel_contract() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window.windowTitle() == "XfinAudio"
    assert window._library_screen.folder_button.text() == "Choose Folder"
    assert window._library_screen.scan_button.text() == "Scan Metadata"
    assert window._library_screen.cancel_button.text() == "Cancel Scan"
    assert window.folder_label.text() == "Library: none"
    assert window.library_guidance_label.text() == "Choose a folder to scan metadata."
    assert window.recommendation_guidance_label.text() == "Scan metadata before recommending a playlist."
    assert window._export_screen.export_guidance_label.text() == (
        "Review recommendations before exporting. "
        "Live Serato writes are not part of the verified release candidate; "
        "back up your library and verify any manual copy."
    )
    assert window.status_label.text() == "Ready"
    assert window._export_screen.safe_export_folder_label.text() == "No safe export folder selected"
    assert window._build_screen.applied_copilot_variant_label.text() == "Applied Variant: none"
    assert window._library_screen.search_input.placeholderText() == "Search songs"
    assert window._build_screen.genre_focus_input.placeholderText() == "Genre focus"
    assert window._build_screen.target_count_input.value() == 25
    assert _table_headers(_library_tracks_table(window)) == [
        "Title",
        "Artist",
        "BPM",
        "Key",
        "Energy",
        "Duration",
        "Color",
        "Missing",
        "Genre",
        "Status",
        "Preview",
        "Path",
    ]
    assert _table_headers(window._review_screen.recommendation_table) == [
        "#",
        "Title",
        "Artist",
        "BPM",
        "Key",
        "Energy",
        "Color",
    ]
    assert _table_headers(window._build_screen.copilot_table) == ["Variant", "Description", "Tracks", "Readiness"]
    assert _table_headers(window._review_screen.transition_table) == [
        "Order",
        "From",
        "To",
        "Key Score",
        "BPM Score",
        "Energy Score",
        "Tag Score",
        "Final Score",
        "Warnings",
    ]
    assert _table_headers(window._export_screen.history_table) == [
        "Time",
        "Strategy",
        "Tracks",
        "Serato Crate",
        "Readiness JSON",
        "Readiness CSV",
    ]
    assert _table_headers(window._review_screen.readiness_table) == ["Check", "Status", "Detail"]

    sidebar_labels = [window.workflow_sidebar.item(index).text() for index in range(window.workflow_sidebar.count())]

    assert isinstance(window.workflow_sidebar, QListWidget)
    assert isinstance(window.workflow_tabs, QStackedWidget)
    assert window.workflow_tabs.count() == 7
    assert sidebar_labels == [
        "Library",
        "Build Playlist",
        "Review Mix",
        "Export to Serato",
        "My Playlists",
        "Metadata Worklist",
        "Live Assistant",
    ]
    assert [
        window.workflow_sidebar.item(index).data(main_window.Qt.ItemDataRole.AccessibleTextRole)
        for index in range(window.workflow_sidebar.count())
    ] == sidebar_labels
    assert window.workflow_sidebar.currentRow() == 0

    assert window._library_screen.scan_button.isEnabled() is False
    assert window._library_screen.cancel_button.isEnabled() is False
    assert window._build_screen.recommend_button.isEnabled() is False
    assert window._export_screen.preview_button.isEnabled() is False
    assert window._export_screen.export_button.isEnabled() is False
    assert window._export_screen.export_readiness_button.isEnabled() is False
    assert window._metadata_screen.export_button.isEnabled() is False
    assert window._build_screen.copilot_button.isEnabled() is False
    assert window._build_screen.apply_variant_button.isEnabled() is False
    assert window._export_screen.history_table.isHidden() is True
    assert window._build_screen.copilot_table.isHidden() is True
    assert window._review_screen.recommendation_table.isHidden() is True
    assert window._review_screen.transition_table.isHidden() is True
    assert window._review_screen.readiness_table.isHidden() is True


def test_main_window_adds_compact_status_bar_hidden_by_default() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window.status_bar.isHidden() is True
    assert window.status_bar.folder_label is window.folder_label
    assert window.status_bar.guidance_label is window.library_guidance_label
    assert window.status_bar.scan_progress_label is window.scan_progress_label
    assert window.status_bar.layout().count() == 3


def test_main_window_places_status_bar_below_workflow_tabs() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    layout = window.centralWidget().layout()
    bottom_row = layout.itemAt(layout.count() - 1).layout()

    assert bottom_row is not None
    assert bottom_row.indexOf(window.status_bar) >= 0


def test_main_window_status_bar_toggle_controls_visibility() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    window.status_bar_toggle.click()
    assert window.status_bar.isHidden() is False

    window.status_bar_toggle.click()
    assert window.status_bar.isHidden() is True


def test_main_window_shows_status_bar_automatically_during_scan(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.set_selected_folder(tmp_path)

    window._begin_scan_state()

    assert window.status_bar.isHidden() is False


def test_main_window_registers_keyboard_shortcuts_and_tooltips() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert {name: _shortcut_text(window, name) for name in window._keyboard_shortcuts} == {
        "open_folder": "Ctrl+O",
        "focus_search": "Ctrl+F",
        "scan_metadata": "Ctrl+Shift+S",
        "recommend_playlist": "Ctrl+R",
        "export_recommendation": "Ctrl+E",
        "toggle_missing_column": "Ctrl+M",
        "open_selected_track": "Return",
        "remove_selected_track": "Del",
        "cancel_scan": "Esc",
        "undo": "Ctrl+Z",
        "redo": "Ctrl+Shift+Z",
    }
    assert window._library_screen.scan_button.toolTip() == "Scan Metadata (Ctrl+Shift+S)"
    assert window._build_screen.recommend_button.toolTip() == "Recommend Playlist (Ctrl+R)"
    assert window._export_screen.export_button.toolTip() == "Export to Serato (Ctrl+E)"


def test_keyboard_shortcuts_trigger_common_actions(tmp_path, monkeypatch) -> None:
    app = ensure_app()
    scan_service = FakeScanService()
    window = MainWindow(scan_service=scan_service, repository=FakeRepository())
    window.show()
    recommend_calls: list[bool] = []
    export_calls: list[bool] = []
    opened: list[list[str]] = []
    window._build_screen.recommend_button.clicked.connect(lambda: recommend_calls.append(True))
    window._export_screen.export_button.clicked.connect(lambda: export_calls.append(True))
    monkeypatch.setattr(main_window.subprocess, "Popen", lambda args: opened.append(args))
    window.set_selected_folder(tmp_path)

    window._keyboard_shortcuts["focus_search"].activated.emit()
    app.processEvents()
    window._keyboard_shortcuts["scan_metadata"].activated.emit()
    _process_events_until(lambda: window.current_scan_cancellation_token is None)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.recommend_button.setEnabled(True)
    window._keyboard_shortcuts["recommend_playlist"].activated.emit()
    window.workflow_tabs.setTabEnabled(3, True)
    window._export_screen.export_button.setEnabled(True)
    window._keyboard_shortcuts["export_recommendation"].activated.emit()
    window._keyboard_shortcuts["toggle_missing_column"].activated.emit()
    window._keyboard_shortcuts["open_selected_track"].activated.emit()
    window.last_recommendation = make_recommendation([window.scanned_records[0]])
    window.show_recommendation([window.scanned_records[0]], "build")
    window._review_screen.recommendation_table.selectRow(0)
    window._keyboard_shortcuts["remove_selected_track"].activated.emit()

    assert window._library_screen.search_input.hasFocus()
    assert scan_service.scanned_folder == tmp_path
    assert recommend_calls == [True]
    assert export_calls == [True]
    assert _library_tracks_table(window).isColumnHidden(_track_table_headers(window).index("Missing")) is False
    assert opened == [["open", str(tmp_path / "track.flac")]]
    assert str(tmp_path / "track.flac") in window.playlist_removed_paths


def test_main_window_table_selection_configuration() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert _library_tracks_table(window).selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectRows
    assert _library_tracks_table(window).selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection
    assert window._build_screen.copilot_table.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectRows
    assert window._build_screen.copilot_table.selectionMode() == QAbstractItemView.SelectionMode.SingleSelection


def test_main_window_displays_initial_empty_state_guidance() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window.library_guidance_label.text() == "Choose a folder to scan metadata."
    assert "Scan metadata before recommending" in window.recommendation_guidance_label.text()
    assert "Review recommendations before exporting" in window._export_screen.export_guidance_label.text()
    assert window._review_screen.review_summary_label.text() == "No recommendation is ready for review."
    assert window._review_screen.transition_table.rowCount() == 0
    assert window._export_screen.safe_export_folder_label.text() == "No safe export folder selected"


def test_main_window_initial_flow_disables_invalid_next_actions() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window._library_screen.scan_button.isEnabled() is False
    assert window._build_screen.recommend_button.isEnabled() is False
    assert window._library_screen.cancel_button.isEnabled() is False


def test_main_window_selecting_folder_enables_scan_but_not_recommendation(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    window.set_selected_folder(tmp_path)

    assert window._library_screen.scan_button.isEnabled() is True
    assert window._build_screen.recommend_button.isEnabled() is False


def test_main_window_changing_folder_clears_stale_scan_and_recommendation_state(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    first_folder = tmp_path / "first"
    second_folder = tmp_path / "second"

    window.set_selected_folder(first_folder)
    window.scan_selected_folder()
    _process_events_until(lambda: window.current_scan_cancellation_token is None)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.strategy_combo.setCurrentText("Warmup")
    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    window.set_selected_folder(second_folder)

    assert window.scanned_records == []
    assert _library_tracks_table(window).rowCount() == 0
    assert window._review_screen.recommendation_table.rowCount() == 0
    assert window._build_screen.recommend_button.isEnabled() is False
    assert window.recommendation_guidance_label.text() == "Scan metadata before recommending a playlist."


def test_main_window_recommendation_becomes_available_only_after_successful_scan_and_selection(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    window.set_selected_folder(tmp_path)
    window.scan_selected_folder()
    _process_events_until(lambda: window.current_scan_cancellation_token is None)

    assert window._build_screen.recommend_button.isEnabled() is False

    _library_tracks_table(window).selectRow(0)

    assert window._build_screen.recommend_button.isEnabled() is True


def test_format_quality_summary_lists_review_counts() -> None:
    report = RecommendationQualityReport(
        track_count=3,
        transition_count=2,
        average_transition_score=0.812345,
        bpm_jumps=[1.0, 2.0],
        energy_jumps=[1, 1],
        warning_count=4,
    )

    assert main_window.format_quality_summary(report) == (
        "Review summary: Tracks: 3 | Transitions: 2 | Average transition score: 0.812 | Warnings: 4"
    )


def test_main_window_displays_existing_safe_export_folder(tmp_path) -> None:
    ensure_app()
    export_folder = tmp_path / "safe-export"
    window = MainWindow(
        scan_service=FakeScanService(),
        repository=FakeRepository(),
        settings=AppSettings(export=ExportSettings(safe_export_folder=export_folder)),
        settings_repository=FakeSettingsRepository(),
    )

    assert window._export_screen.safe_export_folder_label.text() == f"Safe export folder: {export_folder}"


def test_main_window_restores_last_scan_folder_without_clearing_saved_library(tmp_path) -> None:
    ensure_app()
    library_folder = tmp_path / "library"
    window = MainWindow(
        scan_service=FakeScanService(),
        repository=FakeRepository(),
        settings=AppSettings(library=LibrarySettings(last_scan_folder=library_folder)),
    )
    window.restore_persisted_tracks(
        [
            TrackRecord(
                path=str(library_folder / "persisted.flac"),
                title="Persisted",
                metadata_status="complete",
            )
        ]
    )

    assert window.selected_folder == library_folder
    assert _library_tracks_table(window).rowCount() == 1
    assert window._library_screen.scan_button.isEnabled() is True
    assert "refresh metadata" in window.library_guidance_label.toolTip()


def test_main_window_setting_safe_export_folder_persists_and_updates_label(tmp_path) -> None:
    ensure_app()
    settings_repository = FakeSettingsRepository()
    window = MainWindow(
        scan_service=FakeScanService(),
        repository=FakeRepository(),
        settings_repository=settings_repository,
    )
    export_folder = tmp_path / "safe-export"

    window.set_safe_export_folder(export_folder)

    assert window._export_screen.safe_export_folder_label.text() == f"Safe export folder: {export_folder}"
    assert settings_repository.saved_settings is not None
    assert settings_repository.saved_settings.export.safe_export_folder == export_folder


def test_main_window_persists_selected_scan_folder_for_future_refresh(tmp_path) -> None:
    ensure_app()
    settings_repository = FakeSettingsRepository()
    window = MainWindow(
        scan_service=FakeScanService(),
        repository=FakeRepository(),
        settings_repository=settings_repository,
    )

    window.set_selected_folder(tmp_path)

    assert settings_repository.saved_settings is not None
    assert settings_repository.saved_settings.library.last_scan_folder == tmp_path


def test_main_window_rejects_safe_export_folder_equal_to_audio_scan_folder(tmp_path) -> None:
    ensure_app()
    settings_repository = FakeSettingsRepository()
    window = MainWindow(
        scan_service=FakeScanService(),
        repository=FakeRepository(),
        settings_repository=settings_repository,
    )
    window.set_selected_folder(tmp_path)
    saved_after_folder = settings_repository.saved_settings

    window.set_safe_export_folder(tmp_path)

    assert settings_repository.saved_settings == saved_after_folder
    assert settings_repository.saved_settings is not None
    assert settings_repository.saved_settings.export.safe_export_folder is None
    assert window._export_screen.safe_export_folder_label.text() == "No safe export folder selected"
    assert "must be outside the selected audio folder" in window.status_label.text()


def test_main_window_scan_action_populates_table_and_status_counts(tmp_path) -> None:
    ensure_app()
    scan_service = FakeScanService()
    repository = FakeRepository()
    window = MainWindow(scan_service=scan_service, repository=repository)

    window.set_selected_folder(tmp_path)
    window.scan_selected_folder()
    _process_events_until(lambda: window.current_scan_cancellation_token is None)

    assert scan_service.scanned_folder == tmp_path
    assert len(repository.saved_records) == 2
    assert _library_tracks_table(window).rowCount() == 2
    assert window.status_label.text() == "Scan complete: 1 complete, 1 incomplete"


def test_main_window_refresh_reports_metadata_completion_delta(tmp_path) -> None:
    ensure_app()
    track_path = str(tmp_path / "track.flac")
    scan_service = RefreshingScanService(
        [
            TrackRecord(
                path=track_path,
                title="Track",
                bpm=120,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            )
        ]
    )
    window = MainWindow(scan_service=scan_service, repository=FakeRepository())
    window.selected_folder = tmp_path
    window.scanned_records = [
        TrackRecord(
            path=track_path,
            title="Track",
            bpm=120,
            metadata_status="incomplete",
            missing_required_fields=["camelot_key", "energy_level"],
        )
    ]
    window.show_tracks(window.scanned_records)

    window.scan_selected_folder()
    _process_events_until(lambda: window.current_scan_cancellation_token is None)

    assert scan_service.scanned_folder == tmp_path
    assert window.status_label.text() == "Refresh complete: 1 incomplete → 0 incomplete; 1 fixed"


def test_main_window_filters_library_by_song_title(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.show_tracks(
        [
            TrackRecord(
                path=str(tmp_path / "one.flac"),
                title="Love Song",
                artist="Artist",
                metadata_status="complete",
            ),
            TrackRecord(
                path=str(tmp_path / "two.flac"),
                title="Night Drive",
                artist="Love Artist",
                metadata_status="complete",
            ),
            TrackRecord(
                path=str(tmp_path / "three.flac"),
                title="Another Love",
                artist="Singer",
                metadata_status="complete",
            ),
        ]
    )

    window._library_screen.search_input.setText("love")
    window._search_debounce.timeout.emit()

    assert _visible_track_titles(window) == ["Love Song", "Another Love"]


def test_search_filter_debounce_fires_once_for_rapid_input(tmp_path, monkeypatch) -> None:
    """Rapid keystrokes coalesce into a single filter call via the single-shot debounce timer."""
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.show_tracks(
        [
            TrackRecord(path=str(tmp_path / "a.flac"), title="Alpha", metadata_status="complete"),
            TrackRecord(path=str(tmp_path / "b.flac"), title="Beta", metadata_status="complete"),
            TrackRecord(path=str(tmp_path / "c.flac"), title="Gamma", metadata_status="complete"),
        ]
    )

    call_count = 0

    def count_filter(*, clear_selection: bool = False) -> None:
        nonlocal call_count
        call_count += 1

    monkeypatch.setattr(window, "_apply_song_filter", count_filter)

    # Simulate rapid typing: multiple text changes followed by a single debounce fire
    window._library_screen.search_input.setText("a")
    window._library_screen.search_input.setText("al")
    window._library_screen.search_input.setText("alp")
    window._search_debounce.timeout.emit()

    assert call_count == 1


def test_main_window_filters_library_by_metadata_status_and_shows_missing_fields(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    complete_path = str(tmp_path / "complete.flac")
    incomplete_path = str(tmp_path / "incomplete.flac")
    window.scanned_records = [
        TrackRecord(
            path=complete_path,
            title="Ready Track",
            bpm=120,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
        TrackRecord(
            path=incomplete_path,
            title="Needs Tags",
            bpm=120,
            metadata_status="incomplete",
            missing_required_fields=["camelot_key", "energy_level"],
        ),
    ]
    window.show_tracks(window.scanned_records)

    missing_column = _track_table_headers(window).index("Missing")
    window._metadata_screen.status_combo.setCurrentText("Incomplete")

    assert _visible_track_titles(window) == ["Needs Tags"]
    assert _table_item_text(_library_tracks_table(window), 1, missing_column) == "Camelot key, energy level"

    window._metadata_screen.status_combo.setCurrentText("Complete")

    assert _visible_track_titles(window) == ["Ready Track"]


def test_main_window_filters_library_by_specific_missing_metadata_field(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(
            path=str(tmp_path / "needs-key.flac"),
            title="Needs Key",
            metadata_status="incomplete",
            missing_required_fields=["camelot_key"],
        ),
        TrackRecord(
            path=str(tmp_path / "needs-energy.flac"),
            title="Needs Energy",
            metadata_status="incomplete",
            missing_required_fields=["energy_level"],
        ),
        TrackRecord(
            path=str(tmp_path / "ready.flac"),
            title="Ready",
            bpm=120,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
    ]
    window.show_tracks(window.scanned_records)

    window._metadata_screen.missing_combo.setCurrentText("Missing Key")

    assert _visible_track_titles(window) == ["Needs Key"]


def test_main_window_filter_uses_path_index_instead_of_rescanning_records(tmp_path, monkeypatch) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    records = [
        TrackRecord(
            path=str(tmp_path / "needs-key.flac"),
            title="Needs Key",
            metadata_status="incomplete",
            missing_required_fields=["camelot_key"],
        ),
        TrackRecord(
            path=str(tmp_path / "ready.flac"),
            title="Ready",
            bpm=120,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
    ]
    window.show_tracks(records)

    class IterationFails(list):
        def __iter__(self):
            raise AssertionError("filter must use the path index, not iterate scanned_records")

    window.scanned_records = IterationFails(records)
    monkeypatch.setattr(window, "_refresh_idle_action_state", lambda: None)

    window._metadata_screen.missing_combo.setCurrentText("Missing Key")

    assert _visible_track_titles(window) == ["Needs Key"]


def test_populate_track_table_updates_path_mapping_before_reapplying_filter(tmp_path, monkeypatch) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    record = TrackRecord(path=str(tmp_path / "ready.flac"), title="Ready", metadata_status="complete")
    calls: list[tuple[bool, TrackRecord | None]] = []

    def capture_filter(*, clear_selection: bool = False) -> None:
        calls.append((clear_selection, window._records_by_path.get(record.path)))

    monkeypatch.setattr(window, "_apply_song_filter", capture_filter)

    window._populate_track_table([record])

    assert calls == [(False, record)]
    assert window._records_by_path[record.path] is record


def test_main_window_sorts_library_bpm_column_numerically(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.show_tracks(
        [
            TrackRecord(path=str(tmp_path / "high.flac"), title="High", bpm=128, metadata_status="complete"),
            TrackRecord(path=str(tmp_path / "low.flac"), title="Low", bpm=95, metadata_status="complete"),
            TrackRecord(path=str(tmp_path / "mid.flac"), title="Mid", bpm=104, metadata_status="complete"),
        ]
    )

    _library_tracks_table(window).horizontalHeader().sectionClicked.emit(2)

    assert _visible_track_titles(window) == ["Low", "Mid", "High"]


def test_main_window_sorted_selection_maps_to_correct_track_path(tmp_path) -> None:
    ensure_app()
    low_bpm_path = str(tmp_path / "low.flac")
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(path=str(tmp_path / "high.flac"), title="High", bpm=128, metadata_status="complete"),
        TrackRecord(path=low_bpm_path, title="Low", bpm=95, metadata_status="complete"),
    ]
    window.show_tracks(window.scanned_records)

    _library_tracks_table(window).horizontalHeader().sectionClicked.emit(2)
    _library_tracks_table(window).selectRow(0)

    controls = window._selected_track_controls()
    assert controls is not None
    assert controls.start_path == low_bpm_path


def test_main_window_scan_progress_controls_start_disabled() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window._library_screen.cancel_button.text() == "Cancel Scan"
    assert window._library_screen.cancel_button.isEnabled() is False
    assert window.scan_progress_label.text() == "Scan: idle"


def test_main_window_spectral_progress_update_replaces_app_state_immutably() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    previous_state = window._state

    window._on_spectral_progress_updated(2, 5)

    assert window._state is not previous_state
    assert window._state.is_completing_spectral is True
    assert window._state.spectral_progress_count == 2
    assert window._state.spectral_total_count == 5
    assert window._library_screen.status_label.text() == "Analyzing spectral colors 2/5"


def test_main_window_spectral_completion_finished_clears_progress_state() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window._on_spectral_progress_updated(4, 4)
    active_state = window._state

    window._on_spectral_completion_finished()

    assert window._state is not active_state
    assert window._state.is_completing_spectral is False
    assert window._state.spectral_progress_count == 0
    assert window._state.spectral_total_count == 0


def test_main_window_starts_spectral_completion_for_non_current_profiles(monkeypatch) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    worker = Mock()
    worker._thread = None
    monkeypatch.setattr("xfinaudio.desktop.library_controller.SpectralCompletionWorker", Mock(return_value=worker))
    stale = SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
    future = stale.model_copy(update={"analysis_version": CURRENT_ANALYSIS_VERSION + 1})
    current = stale.model_copy(update={"analysis_version": CURRENT_ANALYSIS_VERSION})
    records = [
        TrackRecord(path="/music/stale.flac", spectral_profile=stale),
        TrackRecord(path="/music/future.flac", spectral_profile=future),
        TrackRecord(path="/music/current.flac", spectral_profile=current),
    ]

    window._library_controller.start_spectral_completion_worker(records)

    started_records = worker.start.call_args.args[0]
    assert [record.path for record in started_records] == ["/music/stale.flac", "/music/future.flac"]


def test_main_window_scan_enables_cancel_and_updates_progress_then_disables_on_success(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    window.set_selected_folder(tmp_path)
    window.scan_selected_folder()
    _process_events_until(lambda: window.current_scan_cancellation_token is None)

    assert window._library_screen.cancel_button.isEnabled() is False
    assert window.scan_progress_label.text() == f"Scan progress: 1/2 - {tmp_path / 'track.flac'}"
    assert window.current_scan_cancellation_token is None


def test_main_window_cancel_scan_updates_status_and_token(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.set_selected_folder(tmp_path)
    window._begin_scan_state()

    token = window.current_scan_cancellation_token
    assert token is not None

    window.cancel_scan()

    assert token.is_cancelled is True
    assert window.status_label.text() == "Cancel requested; waiting for current file to finish"
    assert window._library_screen.cancel_button.isEnabled() is False


class CanceledFakeScanService:
    def __init__(self) -> None:
        self.partial_records = [TrackRecord(path="/library/partial.flac", metadata_status="complete")]

    def scan(self, folder: Path, **kwargs) -> list[TrackRecord]:
        progress_callback = kwargs.get("on_progress")
        if progress_callback is not None:
            progress_callback(ScanProgress(processed_count=1, total_count=2, current_path=folder / "partial.flac"))
        raise ScanCancelledError(self.partial_records)


def test_main_window_cancelled_scan_status_and_no_partial_persistence(tmp_path) -> None:
    ensure_app()
    repository = FakeRepository()
    window = MainWindow(scan_service=CanceledFakeScanService(), repository=repository)

    window.set_selected_folder(tmp_path)
    window.scan_selected_folder()
    _process_events_until(lambda: window.current_scan_cancellation_token is None)

    assert repository.saved_records == []
    assert window.scanned_records == []
    assert _library_tracks_table(window).rowCount() == 0
    assert window.status_label.text() == "Scan canceled; no partial results were saved"
    assert window._library_screen.cancel_button.isEnabled() is False


def test_main_window_second_scan_cancels_first_scan(tmp_path) -> None:
    ensure_app()
    scan_service = SlowFakeScanService()
    window = MainWindow(scan_service=scan_service, repository=FakeRepository())
    window.set_selected_folder(tmp_path)

    window.scan_selected_folder()
    assert scan_service.started.wait(timeout=1)

    first_token = window.current_scan_cancellation_token
    assert first_token is not None

    # Start a second scan — this must cancel the first
    window.scan_selected_folder()

    # First scan's token must be cancelled
    assert first_token.is_cancelled is True

    # Let the second scan complete
    scan_service.release.set()
    _process_events_until(lambda: window.current_scan_cancellation_token is None)

    assert _library_tracks_table(window).rowCount() == 2
    assert window.status_label.text() == "Scan complete: 1 complete, 1 incomplete"


def test_main_window_updates_guidance_after_scan_and_recommend(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    window.set_selected_folder(tmp_path)
    window.scan_selected_folder()
    _process_events_until(lambda: window.current_scan_cancellation_token is None)

    assert "Choose a strategy" in window.recommendation_guidance_label.text()
    assert "Recommend Playlist" in window.recommendation_guidance_label.text()

    _library_tracks_table(window).selectRow(0)
    window._build_screen.strategy_combo.setCurrentText("Warmup")
    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    assert "Review scores and warnings" in window._export_screen.export_guidance_label.text()
    assert "safe export" in window._export_screen.export_guidance_label.text()


def test_main_window_recommend_action_populates_playlist_table_and_status(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    window.set_selected_folder(tmp_path)
    window.scan_selected_folder()
    _process_events_until(lambda: window.current_scan_cancellation_token is None)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.strategy_combo.setCurrentText("Warmup")
    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    assert window._review_screen.recommendation_table.rowCount() == 1
    assert window.last_recommendation is not None
    assert window.last_recommendation.ordered_tracks[0].path == str(tmp_path / "track.flac")
    assert window.status_label.text() == "Recommended 1 track(s) using warmup"


def test_main_window_recommendation_uses_single_selected_track_as_start(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(
            path=str(tmp_path / "a.flac"),
            title="A",
            bpm=120.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "b.flac"),
            title="B",
            bpm=120.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
    ]
    window.show_tracks(window.scanned_records)
    window._refresh_idle_action_state()
    _library_tracks_table(window).selectRow(1)

    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    assert window.last_recommendation is not None
    assert window.last_recommendation.ordered_tracks[0].path == str(tmp_path / "b.flac")
    assert window.last_recommendation.applied_controls["start_path"] == str(tmp_path / "b.flac")


def test_main_window_recommendation_uses_multiple_selected_tracks_as_manual_prefix(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(
            path=str(tmp_path / "a.flac"),
            title="A",
            bpm=120.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "b.flac"),
            title="B",
            bpm=120.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "c.flac"),
            title="C",
            bpm=120.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
    ]
    window.show_tracks(window.scanned_records)
    window._refresh_idle_action_state()
    selection_model = _library_tracks_table(window).selectionModel()
    assert selection_model is not None
    selection_model.select(
        _library_tracks_table(window).model().index(0, 0),
        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
    )
    selection_model.select(
        _library_tracks_table(window).model().index(2, 0),
        QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
    )

    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    assert window.last_recommendation is not None
    assert [track.path for track in window.last_recommendation.ordered_tracks[:2]] == [
        str(tmp_path / "a.flac"),
        str(tmp_path / "c.flac"),
    ]
    assert window.last_recommendation.applied_controls["manual_order_paths"] == [
        str(tmp_path / "a.flac"),
        str(tmp_path / "c.flac"),
    ]


def test_main_window_shows_library_screen_track_columns(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    record = TrackRecord(
        path=str(tmp_path / "track.flac"),
        title="Track",
        artist="Artist",
        bpm=124.0,
        camelot_key="8B",
        energy_level=7,
        genre="Disco, Funk & Soul",
        tags=["Boogie", "Peak Mid"],
        metadata_status="complete",
    )

    window.show_tracks([record])
    window.show_recommendation([record], "build")

    track_headers = _table_headers(_library_tracks_table(window))

    assert "Duration" in track_headers
    assert "Genre" in track_headers
    assert "Preview" in track_headers
    assert _table_item_text(_library_tracks_table(window), 0, track_headers.index("Genre")) == "Disco, Funk & Soul"
    assert _table_item_text(_library_tracks_table(window), 0, track_headers.index("Preview")) == "▶"
    # Genre is not shown in the ReviewScreen recommendation table (7 core columns only)
    recommendation_headers = _table_headers(window._review_screen.recommendation_table)
    assert "Genre" not in recommendation_headers


def test_main_window_recommend_action_exposes_transition_explanation_table_data(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(
            path=str(tmp_path / "a.flac"),
            title="A",
            bpm=124.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "b.flac"),
            title="B",
            bpm=125.0,
            camelot_key="8A",
            energy_level=6,
            metadata_status="complete",
        ),
    ]

    window.show_tracks(window.scanned_records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.strategy_combo.setCurrentText("Harmonic Journey")
    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    # Transition scores and warnings are now in the transition_review_table, not recommendation_table
    assert window._review_screen.recommendation_table.rowCount() == 2
    assert window._review_screen.transition_table.rowCount() >= 1
    transition_headers = _table_headers(window._review_screen.transition_table)
    score_item = window._review_screen.transition_table.item(0, transition_headers.index("Final Score"))
    warnings_item = window._review_screen.transition_table.item(0, transition_headers.index("Warnings"))
    assert score_item is not None
    assert score_item.text() != ""
    assert warnings_item is not None


def test_main_window_recommend_action_populates_review_summary(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(
            path=str(tmp_path / "a.flac"),
            title="A",
            bpm=124.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "b.flac"),
            title="B",
            bpm=125.0,
            camelot_key="8A",
            energy_level=6,
            metadata_status="complete",
        ),
    ]

    window.show_tracks(window.scanned_records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.strategy_combo.setCurrentText("Harmonic Journey")
    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    summary = window._review_screen.review_summary_label.text()
    assert "Tracks: 2" in summary
    assert "Transitions: 1" in summary
    assert "Average transition score:" in summary
    assert "Warnings: 1" in summary


def test_main_window_recommend_action_populates_transition_review_table(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(
            path=str(tmp_path / "a.flac"),
            title="A",
            artist="Artist A",
            bpm=124.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "b.flac"),
            title="B",
            artist="Artist B",
            bpm=125.0,
            camelot_key="8A",
            energy_level=6,
            metadata_status="complete",
        ),
    ]

    window.show_tracks(window.scanned_records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.strategy_combo.setCurrentText("Harmonic Journey")
    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    headers = _table_headers(window._review_screen.transition_table)
    assert headers == [
        "Order",
        "From",
        "To",
        "Key Score",
        "BPM Score",
        "Energy Score",
        "Tag Score",
        "Final Score",
        "Warnings",
    ]
    assert window._review_screen.transition_table.rowCount() == 1
    row_values = [_table_item_text(window._review_screen.transition_table, 0, column) for column in range(9)]
    assert row_values[0] == "1"
    assert row_values[1] == "A"
    assert row_values[2] == "B"
    assert row_values[3] != ""
    assert row_values[4] != ""
    assert row_values[5] != ""
    assert row_values[6] == ""
    assert row_values[7] != ""
    assert row_values[8] == main_window.format_recommendation_warning(
        "Tag score unavailable; both tracks have no tags or genre"
    )


def test_main_window_recommend_action_guides_review_table_before_export(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(
            path=str(tmp_path / "a.flac"),
            title="A",
            bpm=124.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "b.flac"),
            title="B",
            bpm=125.0,
            camelot_key="8A",
            energy_level=6,
            metadata_status="complete",
        ),
    ]

    window.show_tracks(window.scanned_records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.strategy_combo.setCurrentText("Harmonic Journey")
    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    guidance = window._export_screen.export_guidance_label.text()
    assert "Inspect the review table" in guidance
    assert "before exporting" in guidance


def test_main_window_recommend_with_no_scanned_records_clears_review_state() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window._review_screen.review_summary_label.setText("stale summary")
    window._review_screen.transition_table.setRowCount(1)

    window.recommend_playlist()

    assert window._review_screen.review_summary_label.text() == "No recommendation is ready for review."
    assert window._review_screen.transition_table.rowCount() == 0


def test_format_recommendation_warning_makes_known_warnings_readable() -> None:
    assert main_window.format_recommendation_warning("left missing required metadata: camelot_key") == (
        "Review metadata: left track is missing Mixed In Key Camelot key metadata. "
        "Re-scan or update tags before relying on this transition."
    )
    assert main_window.format_recommendation_warning("right has invalid Camelot key: not-a-key") == (
        "Review Mixed In Key metadata: right track has invalid Camelot key 'not-a-key'. "
        "Expected values look like 8A or 11B."
    )


def test_format_recommendation_warning_handles_empty_and_unknown_warnings() -> None:
    assert main_window.format_recommendation_warning("") == ""
    assert main_window.format_recommendation_warning("Tag score unavailable; both tracks have no tags or genre") == (
        "Review note: Tag score unavailable; both tracks have no tags or genre"
    )


def test_recommendation_table_formats_warning_cells_without_mutating_raw_explanation(tmp_path) -> None:
    ensure_app()
    left = TrackRecord(path=str(tmp_path / "a.flac"), title="A", metadata_status="complete")
    right = TrackRecord(path=str(tmp_path / "b.flac"), title="B", metadata_status="complete")
    raw_warning = "left missing required metadata: camelot_key"
    explanation = PlaylistExplanation(
        strategy="harmonic_journey",
        optimizer="dynamic_programming",
        track_count=2,
        transition_count=1,
        total_score=0.0,
        warnings=[],
        transitions=[
            TransitionExplanation(
                order=1,
                left=TrackExplanation(path=left.path, title=left.title, metadata_status=left.metadata_status),
                right=TrackExplanation(path=right.path, title=right.title, metadata_status=right.metadata_status),
                component_scores={},
                final_score=0.0,
                warnings=[raw_warning],
                explanations=[],
            )
        ],
    )
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.last_playlist_explanation = explanation
    window.last_recommendation = make_recommendation([left, right])

    window.show_recommendation([left, right], "harmonic_journey", explanation)
    window.show_transition_review(explanation)

    # Transition score and warnings are now in transition_review_table, not recommendation_table
    assert window._review_screen.recommendation_table.isHidden() is False
    assert window._review_screen.recommendation_table.rowCount() == 2
    transition_headers = _table_headers(window._review_screen.transition_table)
    score_item = window._review_screen.transition_table.item(0, transition_headers.index("Final Score"))
    warnings_item = window._review_screen.transition_table.item(0, transition_headers.index("Warnings"))
    assert score_item is not None
    assert warnings_item is not None
    assert score_item.text() == "0.000"
    assert warnings_item.text() == main_window.format_recommendation_warning(raw_warning)
    assert window.last_playlist_explanation.transitions[0].warnings == [raw_warning]


def _process_events_until(predicate, timeout_ms: int = 3000) -> None:
    app = ensure_app()
    deadline = __import__("time").monotonic() + timeout_ms / 1000
    while not predicate():
        app.processEvents()
        if __import__("time").monotonic() > deadline:
            raise AssertionError("condition was not reached while processing Qt events")
        __import__("time").sleep(0.01)


class SlowFakeScanService(FakeScanService):
    def __init__(self) -> None:
        super().__init__()
        self.started = __import__("threading").Event()
        self.release = __import__("threading").Event()

    def scan(self, folder: Path, **kwargs) -> list[TrackRecord]:
        self.started.set()
        self.release.wait(timeout=3)
        return super().scan(folder, **kwargs)


def test_main_window_scan_runs_in_background_without_blocking_ui(tmp_path) -> None:
    ensure_app()
    scan_service = SlowFakeScanService()
    window = MainWindow(scan_service=scan_service, repository=FakeRepository())
    window.set_selected_folder(tmp_path)

    window.scan_selected_folder()

    assert scan_service.started.wait(timeout=1)
    assert window._library_screen.scan_button.isEnabled() is False
    assert window._library_screen.cancel_button.isEnabled() is True
    assert window.status_label.text() == "Scanning metadata"

    scan_service.release.set()
    _process_events_until(lambda: window.current_scan_cancellation_token is None)

    assert _library_tracks_table(window).rowCount() == 2
    assert window.status_label.text() == "Scan complete: 1 complete, 1 incomplete"
    assert window._library_screen.scan_button.isEnabled() is True


class SlowFakeRecommendationWorkflow:
    def __init__(self, result) -> None:
        self.result = result
        self.started = __import__("threading").Event()
        self.release = __import__("threading").Event()

    def recommend(self, records: list[TrackRecord], strategy_name: str, **kwargs):
        self.started.set()
        self.release.wait(timeout=3)
        return self.result


def test_main_window_recommendation_runs_in_background_without_blocking_ui(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(
            path=str(tmp_path / "a.flac"),
            title="A",
            bpm=124.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        )
    ]
    window.show_tracks(window.scanned_records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.strategy_combo.setCurrentText("Warmup")
    expected_result = window.workflow_service.recommend(window.scanned_records, "warmup")
    slow_workflow = SlowFakeRecommendationWorkflow(expected_result)
    window.workflow_service = slow_workflow

    window.recommend_playlist()

    assert slow_workflow.started.wait(timeout=1)
    assert window._build_screen.recommend_button.isEnabled() is False
    assert window.status_label.text() == "Generating recommendation from 1 candidate track(s)"

    slow_workflow.release.set()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    assert window._review_screen.recommendation_table.rowCount() == 1
    assert window.status_label.text() == "Recommended 1 track(s) using warmup"


def test_main_window_with_defaults_restores_persisted_tracks_on_startup(tmp_path) -> None:
    ensure_app()
    from xfinaudio.library.track_repository import TrackRepository

    db_path = tmp_path / "xfinaudio.sqlite3"
    settings_path = tmp_path / "settings.json"
    repository = TrackRepository(db_path)
    repository.save_scan_results(
        [
            TrackRecord(
                path=str(tmp_path / "persisted.flac"),
                title="Persisted",
                bpm=124.0,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            )
        ]
    )

    window = MainWindow.with_defaults(db_path, settings_path)

    assert len(window.scanned_records) == 1
    assert _library_tracks_table(window).rowCount() == 1
    assert _table_item_text(_library_tracks_table(window), 0, 0) == "Persisted"
    assert window.folder_label.text() == "Library: saved"
    assert window.library_guidance_label.text() == "Use filters/search, select a complete track, then recommend."
    assert window.library_guidance_label.toolTip() == (
        "Showing saved library from the app database. Choose a folder to re-scan or update metadata."
    )
    assert window._build_screen.recommend_button.isEnabled() is False
    _library_tracks_table(window).selectRow(0)
    assert window._build_screen.recommend_button.isEnabled() is True
    assert window.status_label.text() == "Loaded saved library: 1 complete, 0 incomplete"


def test_main_window_limits_large_recommendation_candidate_pool_for_interactive_use(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(
            path=str(tmp_path / f"track-{index:03}.flac"),
            title=f"Track {index:03}",
            bpm=120.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        )
        for index in range(100)
    ]
    window.show_tracks(window.scanned_records)
    _library_tracks_table(window).selectRow(80)

    controls = window._selected_track_controls()
    records = window._desktop_recommendation_records(controls)

    assert len(records) == 25
    assert records[0].path == str(tmp_path / "track-080.flac")
    assert str(tmp_path / "track-080.flac") in {record.path for record in records}


def test_main_window_candidate_pool_prefers_selected_track_genre_family(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    selected = TrackRecord(
        path=str(tmp_path / "selected-pop.flac"),
        title="Selected Pop",
        bpm=128.0,
        camelot_key="11B",
        energy_level=7,
        genre="Pop & Dance",
        tags=["Pop & Dance", "Dance-Pop"],
        metadata_status="complete",
    )
    unrelated = [
        TrackRecord(
            path=str(tmp_path / f"unrelated-{index}.flac"),
            title=f"Unrelated {index}",
            bpm=95.0 + index,
            camelot_key="1A",
            energy_level=4,
            genre="Hip-Hop & R&B" if index % 2 else "Rock",
            tags=["Hip-Hop & R&B" if index % 2 else "Rock"],
            metadata_status="complete",
        )
        for index in range(30)
    ]
    compatible = [
        TrackRecord(
            path=str(tmp_path / f"compatible-{index}.flac"),
            title=f"Compatible {index}",
            bpm=126.0 + (index % 4),
            camelot_key="11B",
            energy_level=6 + (index % 2),
            genre="Pop & Dance",
            tags=["Pop & Dance", "Dance-Pop"],
            metadata_status="complete",
        )
        for index in range(30)
    ]
    window.scanned_records = [*unrelated[:15], selected, *unrelated[15:], *compatible]
    window.show_tracks(window.scanned_records)
    _library_tracks_table(window).selectRow(15)

    records = window._desktop_recommendation_records(window._selected_track_controls())

    assert records[0].path == selected.path
    assert len(records) == 25
    assert all(record.genre == "Pop & Dance" for record in records)


def test_main_window_requires_selected_complete_track_before_recommending(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(
            path=str(tmp_path / "track.flac"),
            title="Track",
            bpm=124.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        )
    ]
    window.show_tracks(window.scanned_records)
    window._refresh_idle_action_state()

    assert window._build_screen.recommend_button.isEnabled() is False

    _library_tracks_table(window).selectRow(0)
    window._refresh_idle_action_state()

    assert window._build_screen.recommend_button.isEnabled() is True


def test_main_window_rejects_recommendation_without_selected_track(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(
            path=str(tmp_path / "track.flac"),
            title="Track",
            bpm=124.0,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        )
    ]
    window.show_tracks(window.scanned_records)

    window.recommend_playlist()

    assert window.status_label.text() == "Select at least one complete track before recommending"
    assert window._review_screen.recommendation_table.rowCount() == 0


def test_main_window_exports_last_recommendation_to_serato_crate(tmp_path) -> None:
    ensure_app()
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.last_recommendation = make_recommendation(
        [
            TrackRecord(
                path=str(tmp_path / "dd" / "_Lossless" / "A.flac"),
                title="A",
                bpm=120,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            ),
            TrackRecord(
                path=str(tmp_path / "dd" / "_Lossless" / "B.flac"),
                title="B",
                bpm=121,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            ),
        ]
    )

    window.export_recommendation_to_serato(serato_folder=serato_folder, crate_name="XfinAudio Test")

    target = serato_folder / "Subcrates" / "XfinAudio Test.crate"
    assert target.exists()
    assert "Exported Serato crate" in window.status_label.text()
    assert str(target) in window.status_label.text()


def test_main_window_exports_incomplete_metadata_worklist_to_serato_crate(tmp_path) -> None:
    ensure_app()
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(
            path=str(tmp_path / "dd" / "_Lossless" / "Complete.flac"),
            title="Complete",
            bpm=120,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "dd" / "_Lossless" / "Needs Metadata.flac"),
            title="Needs Metadata",
            bpm=120,
            metadata_status="incomplete",
            missing_required_fields=["camelot_key", "energy_level"],
        ),
    ]
    window.show_tracks(window.scanned_records)

    window.export_metadata_status_to_serato(status="incomplete", serato_folder=serato_folder)

    exported = list((serato_folder / "Subcrates").glob("XfinAudio%%Metadata%%Incomplete%%*.crate"))
    assert len(exported) == 1
    parsed = parse_serato_crate_bytes(exported[0].read_bytes())
    assert parsed.paths == ("_Lossless/Needs Metadata.flac",)
    assert str(exported[0]) in window._export_screen.export_guidance_label.text()
    assert "Scan Metadata" in window._export_screen.export_guidance_label.text()


def test_main_window_exports_specific_missing_key_worklist_to_serato_crate(tmp_path) -> None:
    ensure_app()
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = [
        TrackRecord(
            path=str(tmp_path / "dd" / "_Lossless" / "Needs Key.flac"),
            title="Needs Key",
            metadata_status="incomplete",
            missing_required_fields=["camelot_key"],
        ),
        TrackRecord(
            path=str(tmp_path / "dd" / "_Lossless" / "Needs Energy.flac"),
            title="Needs Energy",
            metadata_status="incomplete",
            missing_required_fields=["energy_level"],
        ),
    ]
    window.show_tracks(window.scanned_records)

    window.export_metadata_status_to_serato(
        status="incomplete",
        missing_field="camelot_key",
        serato_folder=serato_folder,
    )

    exported = list((serato_folder / "Subcrates").glob("XfinAudio%%Metadata%%Missing Key%%*.crate"))
    assert len(exported) == 1
    parsed = parse_serato_crate_bytes(exported[0].read_bytes())
    assert parsed.paths == ("_Lossless/Needs Key.flac",)
    assert "Missing Key" in window.status_label.text()


def test_main_window_serato_export_records_receipt_and_history(tmp_path) -> None:
    ensure_app()
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.last_recommendation = make_recommendation(
        [
            TrackRecord(
                path=str(tmp_path / "dd" / "_Lossless" / "A.flac"),
                title="A",
                bpm=120,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            ),
            TrackRecord(
                path=str(tmp_path / "dd" / "_Lossless" / "B.flac"),
                title="B",
                bpm=121,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            ),
        ]
    )

    window.export_recommendation_to_serato(serato_folder=serato_folder, crate_name="XfinAudio Receipt")

    target = serato_folder / "Subcrates" / "XfinAudio Receipt.crate"
    assert str(target) in window._export_screen.export_guidance_label.text()
    assert window._export_screen.history_table.rowCount() == 1
    assert _table_item_text(window._export_screen.history_table, 0, 1) == "build"
    assert _table_item_text(window._export_screen.history_table, 0, 2) == "2"
    assert _table_item_text(window._export_screen.history_table, 0, 3) == str(target)


def test_main_window_serato_export_history_keeps_five_recent_rows(tmp_path) -> None:
    ensure_app()
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.last_recommendation = make_recommendation(
        [
            TrackRecord(
                path=str(tmp_path / "dd" / "_Lossless" / "Track.flac"),
                title="Track",
                bpm=120,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            )
        ]
    )

    for index in range(6):
        window.export_recommendation_to_serato(serato_folder=serato_folder, crate_name=f"Receipt {index}")

    assert window._export_screen.history_table.rowCount() == 5
    rendered_paths = [_table_item_text(window._export_screen.history_table, row, 3) for row in range(5)]
    assert rendered_paths[0].endswith("Receipt 5.crate")
    assert rendered_paths[-1].endswith("Receipt 1.crate")
    assert all(not path.endswith("Receipt 0.crate") for path in rendered_paths)


def test_main_window_serato_export_button_requires_recommendation(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window._export_screen.export_button.isEnabled() is False

    window.last_recommendation = make_recommendation(
        [
            TrackRecord(
                path=str(tmp_path / "track.flac"),
                title="Track",
                bpm=120,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            )
        ]
    )
    # Export tab also requires a readiness report (Navigation rule).
    window.last_dj_readiness_report = DjReadinessReport(
        status="ready", summary="All good", blocker_count=0, review_count=0, checks=[]
    )
    window._sync_state()

    assert window._export_screen.export_button.isEnabled() is True


def test_main_window_auto_serato_export_preserves_detected_library_volume_root(tmp_path, monkeypatch) -> None:
    ensure_app()
    serato_folder = tmp_path / "Users" / "freddy" / "Music" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    library = export_coordinator.SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path)
    monkeypatch.setattr(export_coordinator, "discover_serato_libraries", lambda: [library])
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.last_recommendation = make_recommendation(
        [
            TrackRecord(
                path=str(tmp_path / "Users" / "freddy" / "Music" / "Track.wav"),
                title="Track",
                bpm=120,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            )
        ]
    )

    window.export_recommendation_to_serato(crate_name="Home Auto")

    parsed = parse_serato_crate_bytes((serato_folder / "Subcrates" / "Home Auto.crate").read_bytes())
    assert parsed.paths == ("Users/freddy/Music/Track.wav",)


def test_main_window_default_serato_export_uses_strategy_grouped_generated_crate(tmp_path, monkeypatch) -> None:
    ensure_app()
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    library = export_coordinator.SeratoLibrary(serato_folder=serato_folder, volume_root=tmp_path / "dd")
    monkeypatch.setattr(export_coordinator, "discover_serato_libraries", lambda: [library])
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.last_recommendation = make_recommendation(
        [
            TrackRecord(
                path=str(tmp_path / "dd" / "_Lossless" / "Track.wav"),
                title="Track",
                bpm=120,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            )
        ]
    )

    window.export_recommendation_to_serato()

    target_folder = serato_folder / "Subcrates"
    exported = list(target_folder.glob("XfinAudio%%Build%%*.crate"))
    assert len(exported) == 1
    assert "build - Track - 1 track" in exported[0].stem
    assert "Exported Serato crate" in window.status_label.text()


def test_desktop_recommendation_pool_uses_path_sets_instead_of_model_equality(monkeypatch) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    selected = TrackRecord(
        path="/music/selected.flac",
        title="Selected",
        bpm=120,
        camelot_key="8A",
        energy_level=5,
        genre="Disco",
        tags=["Disco"],
        metadata_status="complete",
    )
    compatible = [
        TrackRecord(
            path=f"/music/compatible-{index}.flac",
            title=f"Compatible {index}",
            bpm=120 + index * 0.1,
            camelot_key="8A",
            energy_level=5,
            genre="Disco",
            tags=["Disco"],
            metadata_status="complete",
        )
        for index in range(30)
    ]
    fallback = [
        TrackRecord(
            path=f"/music/fallback-{index}.flac",
            title=f"Fallback {index}",
            bpm=120,
            camelot_key="8A",
            energy_level=5,
            genre="Rock",
            tags=["Rock"],
            metadata_status="complete",
        )
        for index in range(30)
    ]
    window.scanned_records = [selected, *compatible, *fallback]

    def fail_on_model_equality(self, other):
        raise AssertionError("candidate pool should compare track paths, not TrackRecord models")

    monkeypatch.setattr(TrackRecord, "__eq__", fail_on_model_equality)

    pool = window._desktop_recommendation_records(DJControls(start_path=selected.path))

    assert pool[0].path == selected.path
    assert len(pool) == 25


def test_main_window_applies_dj_visual_style() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert "#00d4ff" in window.styleSheet()
    assert "#ffb000" in window.styleSheet()
    assert window._export_screen.export_button.objectName() == "seratoExportButton"
    assert window._build_screen.recommend_button.objectName() == "primaryAction"


def test_main_window_uses_compact_macbook_layout_for_library_section() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    layout = window.centralWidget().layout()
    assert layout is not None
    assert layout.spacing() <= 6
    assert _library_tracks_table(window).minimumHeight() >= 400
    assert _library_tracks_table(window).verticalHeader().defaultSectionSize() <= 24
    headers = _track_table_headers(window)
    assert _library_tracks_table(window).columnWidth(headers.index("Genre")) >= 140
    assert _library_tracks_table(window).horizontalHeader().stretchLastSection() is True
    assert "QPushButton#seratoExportButton:disabled" in window.styleSheet()


def test_main_window_collapses_empty_recommendation_sections_to_prioritize_browsing() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window._review_screen.recommendation_table.maximumHeight() <= 80
    assert window._review_screen.transition_table.maximumHeight() <= 80
    assert window._library_screen.search_input.placeholderText() == "Search songs"


def test_main_window_uses_two_row_responsive_command_bars_for_mac_resolution() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window._library_screen.search_input.maximumWidth() <= 220
    assert window._build_screen.genre_focus_input.maximumWidth() <= 360
    assert window._build_screen.recommend_button.minimumWidth() <= 260
    assert window._build_screen.copilot_button.minimumWidth() <= 220
    assert window.folder_label.maximumWidth() <= 260
    assert window.library_guidance_label.maximumWidth() <= 720


def test_main_window_empty_review_hides_empty_result_tables() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window._build_screen.copilot_table.isHidden() is True
    assert window._review_screen.recommendation_table.isHidden() is True
    assert window._review_screen.readiness_table.isHidden() is True
    assert window._review_screen.transition_table.isHidden() is True
    assert window._review_screen.review_summary_label.isHidden() is False
    assert window._review_screen.dj_readiness_label.isHidden() is False


def test_main_window_exposes_dj_workflow_modules_with_decision_points() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    tab_names = [window.workflow_sidebar.item(index).text() for index in range(window.workflow_sidebar.count())]

    assert tab_names == [
        "Library",
        "Build Playlist",
        "Review Mix",
        "Export to Serato",
        "My Playlists",
        "Metadata Worklist",
        "Live Assistant",
    ]
    assert window.workflow_tabs.count() == 7
    assert window.library_decision_label.text() == "DJ Decision Point: choose source, filters, and the track anchor."
    assert (
        window.metadata_decision_label.text()
        == "DJ Decision Point: complete missing metadata, then refresh the library."
    )


def test_main_window_saved_library_status_uses_readable_summary_not_clipped_sentence(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    records = [
        TrackRecord(
            path=str(tmp_path / "ready.flac"),
            title="Ready",
            artist="Artist",
            bpm=120,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
        ),
        TrackRecord(path=str(tmp_path / "missing.flac"), title="Missing", metadata_status="incomplete"),
    ]

    window.restore_persisted_tracks(records)

    assert window.folder_label.text() == "Library: saved"
    assert window.library_guidance_label.text() == "Use filters/search, select a complete track, then recommend."
    assert window.scan_progress_label.text() == "Scan: idle"
    assert window.status_label.text() == "Loaded saved library: 1 complete, 1 incomplete"


def test_main_window_shows_dj_readiness_after_recommendation(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    records = [
        TrackRecord(
            path=str(tmp_path / "a.flac"),
            title="A",
            bpm=120,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["Peak"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "b.flac"),
            title="B",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["Peak"],
            metadata_status="complete",
        ),
    ]

    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    assert "DJ Readiness: Ready" in window._review_screen.dj_readiness_label.text()


def test_main_window_resets_dj_readiness_when_recommendation_is_cleared() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    window._review_screen.dj_readiness_label.setText("DJ Readiness: Ready — previous result")
    window.clear_recommendation_review()

    assert window._review_screen.dj_readiness_label.text() == "DJ Readiness: No recommendation ready."


def _table_texts(table: QTableWidget) -> list[list[str]]:
    return [
        [_table_item_text(table, row, column) for column in range(table.columnCount())]
        for row in range(table.rowCount())
    ]


def test_main_window_renders_dj_readiness_check_table_after_recommendation(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    records = [
        TrackRecord(
            path=str(tmp_path / "a.flac"),
            title="A",
            bpm=120,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["Peak"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "b.flac"),
            title="B",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["Peak"],
            metadata_status="complete",
        ),
    ]

    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    headers = _table_headers(window._review_screen.readiness_table)
    rows = _table_texts(window._review_screen.readiness_table)

    assert headers == ["Check", "Status", "Detail"]
    assert len(rows) >= 5
    assert rows[2][:2] == ["BPM continuity", "Ready"]
    assert any(row[0] == "Average transition score" for row in rows)


def test_main_window_adds_serato_round_trip_check_after_export(tmp_path) -> None:
    ensure_app()
    volume_root = tmp_path / "dd"
    serato_folder = volume_root / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    records: list[TrackRecord] = []
    for name, bpm in [("a.flac", 120), ("b.flac", 121)]:
        path = volume_root / "Music" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"audio")
        records.append(
            TrackRecord(
                path=str(path),
                title=name,
                bpm=bpm,
                camelot_key="8A",
                energy_level=5,
                genre="House",
                tags=["Peak"],
                metadata_status="complete",
            )
        )
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    window.export_recommendation_to_serato(serato_folder=serato_folder)

    rows = _table_texts(window._review_screen.readiness_table)
    serato_rows = [row for row in rows if row[0] == "Serato round-trip"]
    assert serato_rows == [["Serato round-trip", "Ready", "Serato crate validates and 2 track(s) resolve on disk"]]


def test_main_window_clears_dj_readiness_check_table() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window._review_screen.readiness_table.setRowCount(1)

    window.clear_recommendation_review()

    assert window._review_screen.readiness_table.rowCount() == 0


def test_main_window_colors_dj_readiness_status_cells() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    report = DjReadinessReport(
        status="blocked",
        summary="Blocked — 1 blocker(s), 1 review item(s); max BPM jump 10.00%",
        blocker_count=1,
        review_count=1,
        checks=[
            DjReadinessCheck(label="Required metadata", status="ready", detail="All metadata is present"),
            DjReadinessCheck(label="BPM continuity", status="blocked", detail="Max jump is 10.00%"),
            DjReadinessCheck(label="Transition warnings", status="needs_review", detail="1 warning needs review"),
        ],
    )

    window._populate_dj_readiness_table(report)

    readiness_table = window._review_screen.readiness_table
    status_by_check = {
        _table_item_text(readiness_table, row, 0): _table_item(readiness_table, row, 1)
        for row in range(readiness_table.rowCount())
    }

    assert status_by_check["BPM continuity"].text() == "Blocked"
    assert status_by_check["BPM continuity"].background().color().name() == "#ff4d4f"
    assert status_by_check["BPM continuity"].toolTip() == "Blocked: fix before export"
    assert status_by_check["Transition warnings"].text() == "Needs Review"
    assert status_by_check["Transition warnings"].background().color().name() == "#ffb000"
    assert status_by_check["Transition warnings"].toolTip() == "Needs Review: inspect before export"
    assert status_by_check["Required metadata"].text() == "Ready"
    assert status_by_check["Required metadata"].background().color().name() == "#1fd16a"
    assert status_by_check["Required metadata"].toolTip() == "Ready: no action needed"


def test_main_window_exports_dj_readiness_report_files_to_safe_folder(tmp_path) -> None:
    ensure_app()
    safe_folder = tmp_path / "exports"
    safe_folder.mkdir()
    window = MainWindow(
        scan_service=FakeScanService(),
        repository=FakeRepository(),
        settings=AppSettings(export=ExportSettings(safe_export_folder=safe_folder)),
    )
    records = [
        TrackRecord(
            path=str(tmp_path / "a.flac"),
            title="A",
            bpm=120,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["Peak"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "b.flac"),
            title="B",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["Peak"],
            metadata_status="complete",
        ),
    ]
    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    window.export_dj_readiness_report(generated_at=datetime(2026, 6, 6, 9, 30, 0))

    json_path = safe_folder / "xfinaudio-dj-readiness-20260606-093000.json"
    csv_path = safe_folder / "xfinaudio-dj-readiness-20260606-093000.csv"
    assert json_path.exists()
    assert csv_path.exists()
    assert '"status": "ready"' in json_path.read_text(encoding="utf-8")
    assert csv_path.read_text(encoding="utf-8").splitlines()[0] == "check,status,detail"
    assert window.status_label.text() == f"Exported DJ readiness report: {json_path} and {csv_path}"


def test_main_window_rejects_dj_readiness_export_without_recommendation(tmp_path) -> None:
    ensure_app()
    safe_folder = tmp_path / "exports"
    safe_folder.mkdir()
    window = MainWindow(
        scan_service=FakeScanService(),
        repository=FakeRepository(),
        settings=AppSettings(export=ExportSettings(safe_export_folder=safe_folder)),
    )

    window.export_dj_readiness_report()

    assert window.status_label.text() == "Generate a recommendation before exporting DJ readiness"
    assert list(safe_folder.iterdir()) == []


def test_main_window_constructs_prep_copilot_controls() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window._build_screen.copilot_button.text() == "Generate Prep Copilot"
    assert window._build_screen.target_count_input.value() == 25
    assert window._build_screen.genre_focus_input.placeholderText() == "Genre focus"
    assert _header_text(window._build_screen.copilot_table, 0) == "Variant"
    assert _header_text(window._build_screen.copilot_table, 1) == "Description"
    assert _header_text(window._build_screen.copilot_table, 2) == "Tracks"
    assert _header_text(window._build_screen.copilot_table, 3) == "Readiness"


def test_main_window_generates_prep_copilot_variants_from_selected_start(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    records = [
        TrackRecord(
            path=str(tmp_path / "start.flac"),
            title="Start",
            bpm=120,
            camelot_key="8A",
            energy_level=4,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "groove.flac"),
            title="Groove",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "lift.flac"),
            title="Lift",
            bpm=122,
            camelot_key="9A",
            energy_level=6,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
    ]
    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.target_count_input.setValue(3)
    window._build_screen.genre_focus_input.setText("House")

    window.generate_prep_copilot()

    assert window._build_screen.copilot_table.rowCount() == 3
    assert [_table_item_text(window._build_screen.copilot_table, row, 0) for row in range(3)] == [
        "safe",
        "balanced",
        "adventurous",
    ]
    assert {_table_item_text(window._build_screen.copilot_table, row, 3) for row in range(3)} == {"Ready"}
    assert window.last_prep_copilot_plan is not None
    assert all(
        variant.recommendation.ordered_tracks[0].path == str(tmp_path / "start.flac")
        for variant in window.last_prep_copilot_plan.variants
    )
    assert window.status_label.text() == "Generated 3 Prep Copilot variant(s)"


def test_main_window_rejects_prep_copilot_without_complete_selection() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    window.generate_prep_copilot()

    assert window._build_screen.copilot_table.rowCount() == 0
    assert window.status_label.text() == "Select at least one complete track before generating Prep Copilot"


def test_main_window_applies_selected_prep_copilot_variant_to_review_flow(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    records = [
        TrackRecord(
            path=str(tmp_path / "start.flac"),
            title="Start",
            bpm=120,
            camelot_key="8A",
            energy_level=4,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "groove.flac"),
            title="Groove",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "lift.flac"),
            title="Lift",
            bpm=122,
            camelot_key="9A",
            energy_level=6,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
    ]
    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.target_count_input.setValue(3)
    window._build_screen.genre_focus_input.setText("House")
    window.generate_prep_copilot()
    window._build_screen.copilot_table.selectRow(1)

    window.apply_selected_prep_copilot_variant()

    assert window.last_recommendation is not None
    assert window.last_prep_copilot_plan is not None
    assert window.last_recommendation == window.last_prep_copilot_plan.variants[1].recommendation
    assert window._review_screen.recommendation_table.rowCount() == 3
    assert window._review_screen.transition_table.rowCount() == 2
    assert window._review_screen.readiness_table.rowCount() > 0
    assert window._export_screen.export_button.isEnabled() is True
    assert window.status_label.text() == "Applied Prep Copilot variant: balanced"


def test_main_window_rejects_apply_prep_copilot_without_variant_selection(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    window.apply_selected_prep_copilot_variant()

    assert window.status_label.text() == "Generate and select a Prep Copilot variant before applying"
    assert window._review_screen.recommendation_table.rowCount() == 0


def test_main_window_exports_applied_prep_copilot_variant_with_variant_crate_name(tmp_path) -> None:
    ensure_app()
    volume_root = tmp_path / "dd"
    serato_folder = volume_root / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    records = [
        TrackRecord(
            path=str(volume_root / "Music" / "start.flac"),
            title="Start",
            bpm=120,
            camelot_key="8A",
            energy_level=4,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(volume_root / "Music" / "groove.flac"),
            title="Groove",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
    ]
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.target_count_input.setValue(2)
    window._build_screen.genre_focus_input.setText("House")
    window.generate_prep_copilot()
    window._build_screen.copilot_table.selectRow(1)
    window.apply_selected_prep_copilot_variant()

    window.export_recommendation_to_serato(
        serato_folder=serato_folder,
        generated_at=datetime(2026, 6, 6, 14, 30, 0),
    )

    expected_name = (
        "XfinAudio%%Prep Copilot%%Harmonic Journey%%Balanced%%"
        "20260606-143000 - harmonic_journey - balanced - Start - 2 tracks.crate"
    )
    expected = serato_folder / "Subcrates" / expected_name
    assert expected.exists()
    assert str(expected) in window.status_label.text()


def test_main_window_constructs_serato_export_preview_action() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window._export_screen.preview_button.text() == "Preview Serato Export"
    assert window._export_screen.preview_button.isEnabled() is False


def test_main_window_previews_applied_copilot_serato_export_without_writing(tmp_path) -> None:
    ensure_app()
    volume_root = tmp_path / "dd"
    serato_folder = volume_root / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    records = [
        TrackRecord(
            path=str(volume_root / "Music" / "start.flac"),
            title="Start",
            bpm=120,
            camelot_key="8A",
            energy_level=4,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(volume_root / "Music" / "groove.flac"),
            title="Groove",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
    ]
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.target_count_input.setValue(2)
    window._build_screen.genre_focus_input.setText("House")
    window.generate_prep_copilot()
    window._build_screen.copilot_table.selectRow(1)
    window.apply_selected_prep_copilot_variant()

    window.preview_serato_export(
        serato_folder=serato_folder,
        generated_at=datetime(2026, 6, 6, 14, 30, 0),
    )

    expected_name = (
        "XfinAudio%%Prep Copilot%%Harmonic Journey%%Balanced%%"
        "20260606-143000 - harmonic_journey - balanced - Start - 2 tracks.crate"
    )
    expected = serato_folder / "Subcrates" / expected_name
    assert not expected.exists()
    assert window.status_label.text() == f"Serato export preview: {expected}"
    assert "Variant: balanced" in window._export_screen.export_guidance_label.text()
    assert "Tracks: 2" in window._export_screen.export_guidance_label.text()
    assert "Will write: yes" in window._export_screen.export_guidance_label.text()
    assert "Readiness: Ready" in window._export_screen.export_guidance_label.text()


def test_main_window_previews_collision_suffix_without_overwriting(tmp_path) -> None:
    ensure_app()
    volume_root = tmp_path / "dd"
    serato_folder = volume_root / "_Serato_"
    target_folder = serato_folder / "Subcrates"
    target_folder.mkdir(parents=True)
    existing_name = "XfinAudio%%Build%%20260606-143000 - build - Start - 2 tracks.crate"
    existing = target_folder / existing_name
    existing.write_bytes(b"existing")
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.last_recommendation = make_recommendation(
        [
            TrackRecord(
                path=str(volume_root / "Music" / "start.flac"),
                title="Start",
                bpm=120,
                camelot_key="8A",
                energy_level=4,
                metadata_status="complete",
            ),
            TrackRecord(
                path=str(volume_root / "Music" / "groove.flac"),
                title="Groove",
                bpm=121,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            ),
        ]
    )

    window.preview_serato_export(
        serato_folder=serato_folder,
        generated_at=datetime(2026, 6, 6, 14, 30, 0),
    )

    expected = target_folder / "XfinAudio%%Build%%20260606-143000 - build - Start - 2 tracks-2.crate"
    assert existing.read_bytes() == b"existing"
    assert not expected.exists()
    assert window.status_label.text() == f"Serato export preview: {expected}"


def test_main_window_exports_dj_readiness_sidecar_reports_with_serato_crate(tmp_path) -> None:
    ensure_app()
    volume_root = tmp_path / "dd"
    serato_folder = volume_root / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    records = [
        TrackRecord(
            path=str(volume_root / "Music" / "start.flac"),
            title="Start",
            bpm=120,
            camelot_key="8A",
            energy_level=4,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(volume_root / "Music" / "groove.flac"),
            title="Groove",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
    ]
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.target_count_input.setValue(2)
    window._build_screen.genre_focus_input.setText("House")
    window.generate_prep_copilot()
    window._build_screen.copilot_table.selectRow(1)
    window.apply_selected_prep_copilot_variant()

    window.export_recommendation_to_serato(
        serato_folder=serato_folder,
        generated_at=datetime(2026, 6, 6, 14, 30, 0),
    )

    crate_name = (
        "XfinAudio%%Prep Copilot%%Harmonic Journey%%Balanced%%"
        "20260606-143000 - harmonic_journey - balanced - Start - 2 tracks.crate"
    )
    crate_path = serato_folder / "Subcrates" / crate_name
    json_path = crate_path.with_suffix(".dj-readiness.json")
    csv_path = crate_path.with_suffix(".dj-readiness.csv")
    assert crate_path.exists()
    assert json_path.exists()
    assert csv_path.exists()
    assert '"status": "ready"' in json_path.read_text(encoding="utf-8")
    assert csv_path.read_text(encoding="utf-8").splitlines()[0] == "check,status,detail"
    assert f"Readiness reports: {json_path} and {csv_path}" in window._export_screen.export_guidance_label.text()


def test_main_window_colors_prep_copilot_readiness_cells(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    records = [
        TrackRecord(
            path=str(tmp_path / "start.flac"),
            title="Start",
            bpm=120,
            camelot_key="8A",
            energy_level=4,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "groove.flac"),
            title="Groove",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
    ]
    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.target_count_input.setValue(2)
    window.generate_prep_copilot()

    readiness_item = _table_item(window._build_screen.copilot_table, 0, 3)

    assert readiness_item.text() == "Ready"
    assert readiness_item.background().color().name() == "#1fd16a"
    assert readiness_item.toolTip().startswith("Ready")


def test_main_window_double_click_applies_prep_copilot_variant(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    records = [
        TrackRecord(
            path=str(tmp_path / "start.flac"),
            title="Start",
            bpm=120,
            camelot_key="8A",
            energy_level=4,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "groove.flac"),
            title="Groove",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
    ]
    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.target_count_input.setValue(2)
    window.generate_prep_copilot()

    item = _table_item(window._build_screen.copilot_table, 2, 0)
    window._build_screen.copilot_table.itemDoubleClicked.emit(item)

    assert window.last_prep_copilot_plan is not None
    assert window.last_recommendation == window.last_prep_copilot_plan.variants[2].recommendation
    assert window.status_label.text() == "Applied Prep Copilot variant: adventurous"


def test_main_window_shows_empty_applied_copilot_variant_badge_initially() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window._build_screen.applied_copilot_variant_label.text() == "Applied Variant: none"


def test_main_window_updates_applied_copilot_variant_badge_after_apply(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    records = [
        TrackRecord(
            path=str(tmp_path / "start.flac"),
            title="Start",
            bpm=120,
            camelot_key="8A",
            energy_level=4,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "groove.flac"),
            title="Groove",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
    ]
    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.target_count_input.setValue(2)
    window.generate_prep_copilot()
    window._build_screen.copilot_table.selectRow(1)

    window.apply_selected_prep_copilot_variant()

    applied_variant_label = window._build_screen.applied_copilot_variant_label
    assert applied_variant_label.text() == "Applied Variant: balanced"
    assert applied_variant_label.toolTip() == "This variant will be used for Serato preview/export."


def test_main_window_clears_applied_copilot_variant_badge_for_normal_recommendation(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    records = [
        TrackRecord(
            path=str(tmp_path / "start.flac"),
            title="Start",
            bpm=120,
            camelot_key="8A",
            energy_level=4,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "groove.flac"),
            title="Groove",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
    ]
    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.target_count_input.setValue(2)
    window.generate_prep_copilot()
    window._build_screen.copilot_table.selectRow(1)
    window.apply_selected_prep_copilot_variant()

    window.recommend_playlist()
    _process_events_until(lambda: window._build_screen.recommend_button.isEnabled())

    assert window._build_screen.applied_copilot_variant_label.text() == "Applied Variant: none"


def test_main_window_serato_export_history_includes_readiness_sidecar_paths(tmp_path) -> None:
    ensure_app()
    volume_root = tmp_path / "dd"
    serato_folder = volume_root / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    records = [
        TrackRecord(
            path=str(volume_root / "Music" / "start.flac"),
            title="Start",
            bpm=120,
            camelot_key="8A",
            energy_level=4,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(volume_root / "Music" / "groove.flac"),
            title="Groove",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        ),
    ]
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.scanned_records = records
    window.show_tracks(records)
    _library_tracks_table(window).selectRow(0)
    window._build_screen.target_count_input.setValue(2)
    window.generate_prep_copilot()
    window._build_screen.copilot_table.selectRow(1)
    window.apply_selected_prep_copilot_variant()

    window.export_recommendation_to_serato(
        serato_folder=serato_folder,
        generated_at=datetime(2026, 6, 6, 14, 30, 0),
    )

    crate_path = Path(window.serato_export_history[0]["path"])
    assert window._export_screen.history_table.columnCount() == 6
    assert _header_text(window._export_screen.history_table, 4) == "Readiness JSON"
    assert _header_text(window._export_screen.history_table, 5) == "Readiness CSV"
    assert _table_item_text(window._export_screen.history_table, 0, 4) == str(
        crate_path.with_suffix(".dj-readiness.json")
    )
    assert _table_item_text(window._export_screen.history_table, 0, 5) == str(
        crate_path.with_suffix(".dj-readiness.csv")
    )


def test_main_window_blocks_serato_export_when_dj_readiness_is_blocked(tmp_path) -> None:
    ensure_app()
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.last_recommendation = make_recommendation(
        [
            TrackRecord(
                path=str(tmp_path / "dd" / "_Lossless" / "A.flac"),
                title="A",
                bpm=120,
                camelot_key="8A",
                energy_level=5,
                metadata_status="complete",
            ),
        ]
    )
    window.last_dj_readiness_report = DjReadinessReport(
        status="blocked",
        summary="Blocked for testing",
        checks=[DjReadinessCheck(label="BPM jump", status="blocked", detail="Too large")],
        blocker_count=1,
        review_count=0,
    )

    window.export_recommendation_to_serato(serato_folder=serato_folder, crate_name="Blocked Test")

    target = serato_folder / "Subcrates" / "Blocked Test.crate"
    assert not target.exists()
    assert "Resolve blocked readiness checks before exporting" in window.status_label.text()


# ----------------------------------------------------------------------
# Phase 5: Responsive layout, full screen, geometry persistence
# ----------------------------------------------------------------------


def test_responsive_sidebar_width_is_wide_at_or_above_breakpoint() -> None:
    breakpoint = main_window._NARROW_BREAKPOINT

    assert main_window.responsive_sidebar_width(breakpoint) == main_window._SIDEBAR_WIDTH_WIDE
    assert main_window.responsive_sidebar_width(breakpoint + 400) == main_window._SIDEBAR_WIDTH_WIDE


def test_responsive_sidebar_width_is_narrow_below_breakpoint() -> None:
    breakpoint = main_window._NARROW_BREAKPOINT

    assert main_window.responsive_sidebar_width(breakpoint - 1) == main_window._SIDEBAR_WIDTH_NARROW
    assert main_window.responsive_sidebar_width(320) == main_window._SIDEBAR_WIDTH_NARROW


def test_responsive_sidebar_widths_differ() -> None:
    assert main_window._SIDEBAR_WIDTH_WIDE == 180
    assert main_window._SIDEBAR_WIDTH_NARROW == 120


def test_main_window_narrow_resize_collapses_sidebar_to_icons() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    window._apply_responsive_layout(main_window._NARROW_BREAKPOINT - 1)

    assert window._sidebar_panel.width() == main_window._SIDEBAR_WIDTH_NARROW
    visible_labels = [window.workflow_sidebar.item(i).text() for i in range(window.workflow_sidebar.count())]
    assert visible_labels == ["" for _ in visible_labels]


def test_main_window_wide_resize_restores_sidebar_labels() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window._apply_responsive_layout(main_window._NARROW_BREAKPOINT - 1)

    window._apply_responsive_layout(main_window._NARROW_BREAKPOINT + 100)

    assert window._sidebar_panel.width() == main_window._SIDEBAR_WIDTH_WIDE
    visible_labels = [window.workflow_sidebar.item(i).text() for i in range(window.workflow_sidebar.count())]
    assert visible_labels == [
        "Library",
        "Build Playlist",
        "Review Mix",
        "Export to Serato",
        "My Playlists",
        "Metadata Worklist",
        "Live Assistant",
    ]


def test_main_window_full_screen_hides_sidebar_and_status_controls() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.show()

    window.set_full_screen(True)

    assert window._sidebar_panel.isHidden() is True
    assert window.status_bar_toggle.isHidden() is True


def test_main_window_exit_full_screen_restores_sidebar_and_status_controls() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.show()
    window.set_full_screen(True)

    window.set_full_screen(False)

    assert window._sidebar_panel.isHidden() is False
    assert window.status_bar_toggle.isHidden() is False


def test_main_window_restores_persisted_window_geometry() -> None:
    ensure_app()
    window = MainWindow(
        scan_service=FakeScanService(),
        repository=FakeRepository(),
        settings=AppSettings(window=WindowSettings(width=1100, height=720, x=20, y=30)),
    )

    assert window.width() == 1100
    assert window.height() == 720


def test_main_window_persists_window_geometry_on_close() -> None:
    ensure_app()
    settings_repository = FakeSettingsRepository()
    window = MainWindow(
        scan_service=FakeScanService(),
        repository=FakeRepository(),
        settings_repository=settings_repository,
    )
    window.resize(1024, 680)

    window.closeEvent(QCloseEvent())

    assert settings_repository.saved_settings is not None
    assert settings_repository.saved_settings.window.width == 1024
    assert settings_repository.saved_settings.window.height == 680


def test_track_removal_is_undoable_and_redoable(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    path = str(tmp_path / "track.flac")

    window._on_track_remove_requested(path)
    assert path in window.playlist_removed_paths

    window.undo()
    assert path not in window.playlist_removed_paths

    window.redo()
    assert path in window.playlist_removed_paths

    window._on_track_remove_requested(str(tmp_path / "a.flac"))
    window._on_track_remove_requested(str(tmp_path / "b.flac"))
    assert window.undo_history_menu.actions()[0].text() == "Remove b.flac"


def test_track_removal_backfills_recommendation_and_undo_restores_it() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    def _record(path: str, bpm: float, key: str, energy: int) -> TrackRecord:
        return TrackRecord(
            path=path,
            title=path,
            bpm=bpm,
            camelot_key=key,
            energy_level=energy,
            metadata_status="complete",
        )

    left = _record("/left.flac", 120.0, "8A", 4)
    mid = _record("/mid.flac", 121.0, "9A", 5)
    right = _record("/right.flac", 122.0, "10A", 6)
    spare = _record("/spare.flac", 121.0, "9A", 5)
    window.scanned_records = [left, mid, right, spare]
    original = make_recommendation([left, mid, right])
    window.last_recommendation = original

    window._on_track_remove_requested("/mid.flac")

    assert "/mid.flac" in window.playlist_removed_paths
    backfilled_paths = [item.path for item in window.last_recommendation.ordered_tracks]
    assert "/mid.flac" not in backfilled_paths
    assert "/spare.flac" in backfilled_paths
    assert len(backfilled_paths) == 3

    window.undo()
    assert "/mid.flac" not in window.playlist_removed_paths
    assert [item.path for item in window.last_recommendation.ordered_tracks] == [
        item.path for item in original.ordered_tracks
    ]

    window.redo()
    assert "/mid.flac" in window.playlist_removed_paths
    assert "/spare.flac" in [item.path for item in window.last_recommendation.ordered_tracks]


def test_clearing_library_filters_is_undoable() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    library = window._library_screen
    library.complete_filter_button.setChecked(True)

    library.clear_filters_button.click()
    assert library.complete_filter_button.isChecked() is False
    assert window.undo_history_menu.actions()[0].text() == "Clear filters"

    window.undo()
    assert library.complete_filter_button.isChecked() is True

    window.redo()
    assert library.complete_filter_button.isChecked() is False
    assert [action.text() for action in window.undo_history_menu.actions()] == ["Clear filters"]


def test_playlist_reorder_is_undoable_and_redoable(monkeypatch) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    editor = window._playlist_editor
    editor._playlist_id = 7
    original = ["/music/a.flac", "/music/b.flac"]
    reordered = list(reversed(original))
    editor._track_paths = original
    monkeypatch.setattr(window._playlist_repository, "update_tracks", lambda playlist_id, paths: None)
    monkeypatch.setattr(window._playlist_coordinator, "refresh_list", lambda: None)

    window._playlist_coordinator._on_tracks_reordered(reordered)

    assert editor._track_paths == reordered
    assert window.undo_history_menu.actions()[0].text() == "Reorder playlist"

    window.undo()
    assert editor._track_paths == original

    window.redo()
    assert editor._track_paths == reordered
