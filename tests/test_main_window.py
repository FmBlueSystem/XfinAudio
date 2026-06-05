from pathlib import Path

from PySide6.QtWidgets import QApplication

from xfinaudio.config.settings import AppSettings, ExportSettings
from xfinaudio.desktop import main_window
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.exporting.explainability import PlaylistExplanation, TrackExplanation, TransitionExplanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancelledError, ScanProgress
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport


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

    def save(self, settings: AppSettings) -> None:
        self.saved_settings = settings


def test_main_window_constructs_desktop_scanning_skeleton() -> None:
    app = ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window.windowTitle() == "XfinAudio"
    assert window.folder_button.text() == "Choose Folder"
    assert window.scan_button.text() == "Scan Metadata"
    assert window.strategy_combo.count() == 7
    assert window.recommend_button.text() == "Recommend Playlist"
    assert window.tracks_table.columnCount() >= 7
    assert window.recommendation_table.columnCount() >= 7
    assert app is not None


def test_main_window_displays_initial_empty_state_guidance() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert "Choose a Mixed In Key processed folder" in window.library_guidance_label.text()
    assert "Scan metadata before recommending" in window.recommendation_guidance_label.text()
    assert "Review recommendations before exporting" in window.export_guidance_label.text()
    assert window.review_summary_label.text() == "No recommendation is ready for review."
    assert window.transition_review_table.rowCount() == 0
    assert window.safe_export_folder_label.text() == "No safe export folder selected"


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

    assert window.safe_export_folder_label.text() == f"Safe export folder: {export_folder}"


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

    assert window.safe_export_folder_label.text() == f"Safe export folder: {export_folder}"
    assert settings_repository.saved_settings is not None
    assert settings_repository.saved_settings.export.safe_export_folder == export_folder


def test_main_window_rejects_safe_export_folder_equal_to_audio_scan_folder(tmp_path) -> None:
    ensure_app()
    settings_repository = FakeSettingsRepository()
    window = MainWindow(
        scan_service=FakeScanService(),
        repository=FakeRepository(),
        settings_repository=settings_repository,
    )
    window.set_selected_folder(tmp_path)

    window.set_safe_export_folder(tmp_path)

    assert settings_repository.saved_settings is None
    assert window.safe_export_folder_label.text() == "No safe export folder selected"
    assert "must be outside the selected audio folder" in window.status_label.text()


def test_main_window_scan_action_populates_table_and_status_counts(tmp_path) -> None:
    ensure_app()
    scan_service = FakeScanService()
    repository = FakeRepository()
    window = MainWindow(scan_service=scan_service, repository=repository)

    window.set_selected_folder(tmp_path)
    window.scan_selected_folder()

    assert scan_service.scanned_folder == tmp_path
    assert len(repository.saved_records) == 2
    assert window.tracks_table.rowCount() == 2
    assert window.status_label.text() == "Scan complete: 1 complete, 1 incomplete"


def test_main_window_scan_progress_controls_start_disabled() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    assert window.cancel_scan_button.text() == "Cancel Scan"
    assert window.cancel_scan_button.isEnabled() is False
    assert window.scan_progress_label.text() == "Scan progress: idle"


def test_main_window_scan_enables_cancel_and_updates_progress_then_disables_on_success(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    window.set_selected_folder(tmp_path)
    window.scan_selected_folder()

    assert window.cancel_scan_button.isEnabled() is False
    assert window.scan_progress_label.text() == f"Scan progress: 1/2 - {tmp_path / 'track.flac'}"
    assert window.current_scan_cancellation_token is None


def test_main_window_cancel_scan_updates_status_and_token(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.set_selected_folder(tmp_path)
    window._begin_scan_state()
    token = window.current_scan_cancellation_token

    window.cancel_scan()

    assert token is not None
    assert token.is_cancelled is True
    assert window.status_label.text() == "Cancel requested; waiting for current file to finish"
    assert window.cancel_scan_button.isEnabled() is False


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

    assert repository.saved_records == []
    assert window.scanned_records == []
    assert window.tracks_table.rowCount() == 0
    assert window.status_label.text() == "Scan canceled; no partial results were saved"
    assert window.cancel_scan_button.isEnabled() is False


def test_main_window_updates_guidance_after_scan_and_recommend(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    window.set_selected_folder(tmp_path)
    window.scan_selected_folder()

    assert "Choose a strategy" in window.recommendation_guidance_label.text()
    assert "Recommend Playlist" in window.recommendation_guidance_label.text()

    window.strategy_combo.setCurrentText("warmup")
    window.recommend_playlist()

    assert "Review scores and warnings" in window.export_guidance_label.text()
    assert "safe export" in window.export_guidance_label.text()


def test_main_window_recommend_action_populates_playlist_table_and_status(tmp_path) -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())

    window.set_selected_folder(tmp_path)
    window.scan_selected_folder()
    window.strategy_combo.setCurrentText("warmup")
    window.recommend_playlist()

    assert window.recommendation_table.rowCount() == 1
    path_item = window.recommendation_table.item(0, 6)
    assert path_item is not None
    assert path_item.text() == str(tmp_path / "track.flac")
    assert window.status_label.text() == "Recommended 1 track(s) using warmup"


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

    window.strategy_combo.setCurrentText("harmonic_journey")
    window.recommend_playlist()

    assert window.recommendation_table.columnCount() >= 9
    score_item = window.recommendation_table.item(1, 7)
    warnings_item = window.recommendation_table.item(1, 8)
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

    window.strategy_combo.setCurrentText("harmonic_journey")
    window.recommend_playlist()

    summary = window.review_summary_label.text()
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

    window.strategy_combo.setCurrentText("harmonic_journey")
    window.recommend_playlist()

    headers = [
        window.transition_review_table.horizontalHeaderItem(column).text()
        for column in range(window.transition_review_table.columnCount())
    ]
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
    assert window.transition_review_table.rowCount() == 1
    row_values = [window.transition_review_table.item(0, column).text() for column in range(9)]
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

    window.strategy_combo.setCurrentText("harmonic_journey")
    window.recommend_playlist()

    guidance = window.export_guidance_label.text()
    assert "Inspect the review table" in guidance
    assert "before exporting" in guidance


def test_main_window_recommend_with_no_scanned_records_clears_review_state() -> None:
    ensure_app()
    window = MainWindow(scan_service=FakeScanService(), repository=FakeRepository())
    window.review_summary_label.setText("stale summary")
    window.transition_review_table.setRowCount(1)

    window.recommend_playlist()

    assert window.review_summary_label.text() == "No recommendation is ready for review."
    assert window.transition_review_table.rowCount() == 0


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

    window.show_recommendation([left, right], "harmonic_journey", explanation)

    warnings_item = window.recommendation_table.item(1, 8)
    assert warnings_item is not None
    assert warnings_item.text() == main_window.format_recommendation_warning(raw_warning)
    assert window.last_playlist_explanation.transitions[0].warnings == [raw_warning]
