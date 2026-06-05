"""PySide6 desktop walking skeleton for XfinAudio."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService, ScanService, TrackPersistence
from xfinaudio.config.settings import AppSettings, ExportSettings
from xfinaudio.exporting.explainability import PlaylistExplanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import MetadataScanService, ScanCancellationToken, ScanProgress
from xfinaudio.library.track_repository import TrackRepository
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import available_strategies


class SettingsPersistence(Protocol):
    """Persistence boundary for app settings updates from the desktop UI."""

    def save(self, settings: AppSettings) -> None:
        """Persist application settings."""


_FIELD_LABELS = {
    "bpm": "BPM",
    "camelot_key": "Camelot key",
    "energy_level": "energy level",
}

_EMPTY_REVIEW_SUMMARY = "No recommendation is ready for review."
_TRANSITION_REVIEW_HEADERS = [
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


def format_quality_summary(report: RecommendationQualityReport) -> str:
    """Return a desktop-friendly quality summary for a recommendation report."""
    return (
        "Review summary: "
        f"Tracks: {report.track_count} | "
        f"Transitions: {report.transition_count} | "
        f"Average transition score: {report.average_transition_score:.3f} | "
        f"Warnings: {report.warning_count}"
    )


def _format_review_score(score: float | None) -> str:
    """Format a transition review score or return an empty cell for unavailable scores."""
    if score is None:
        return ""
    return f"{score:.3f}"


def _track_review_name(track: object) -> str:
    """Return a compact track label for transition review cells."""
    title = getattr(track, "title", None)
    if title:
        return str(title)
    return str(getattr(track, "path", ""))


def _component_score(transition: object, field_name: str, component_name: str) -> float | None:
    """Read preferred explanation score fields while preserving explicit zero scores."""
    score = getattr(transition, field_name, None)
    if score is not None:
        return score
    component_scores = getattr(transition, "component_scores", {})
    return component_scores.get(component_name)


def format_recommendation_warning(raw_warning: str) -> str:
    """Return desktop-friendly text for a raw recommendation warning."""
    warning = raw_warning.strip()
    if not warning:
        return ""

    missing_marker = " missing required metadata: "
    if missing_marker in warning:
        side, _, fields_text = warning.partition(missing_marker)
        fields = [_FIELD_LABELS.get(field.strip(), field.strip().replace("_", " ")) for field in fields_text.split(",")]
        return (
            f"Review metadata: {side} track is missing Mixed In Key {', '.join(fields)} metadata. "
            "Re-scan or update tags before relying on this transition."
        )

    invalid_marker = " has invalid Camelot key: "
    if invalid_marker in warning:
        side, _, key = warning.partition(invalid_marker)
        return (
            f"Review Mixed In Key metadata: {side} track has invalid Camelot key {key!r}. "
            "Expected values look like 8A or 11B."
        )

    if warning == "invalid Camelot key":
        return "Review Mixed In Key metadata: at least one transition has an invalid Camelot key."

    return f"Review note: {warning}"


class MainWindow(QMainWindow):
    """Main desktop window for the HELP-4 metadata scanning skeleton."""

    def __init__(
        self,
        *,
        scan_service: ScanService,
        repository: TrackPersistence,
        settings: AppSettings | None = None,
        settings_repository: SettingsPersistence | None = None,
    ) -> None:
        super().__init__()
        self.workflow_service = PlaylistWorkflowService(scan_service=scan_service, repository=repository)
        self.settings = settings or AppSettings()
        self.settings_repository = settings_repository
        self.selected_folder: Path | None = None
        self.scanned_records: list[TrackRecord] = []
        self.last_recommendation: PlaylistRecommendation | None = None
        self.last_playlist_explanation: PlaylistExplanation | None = None
        self.last_quality_report: RecommendationQualityReport | None = None
        self.current_scan_cancellation_token: ScanCancellationToken | None = None

        self.setWindowTitle("XfinAudio")
        self.folder_button = QPushButton("Choose Folder")
        self.scan_button = QPushButton("Scan Metadata")
        self.cancel_scan_button = QPushButton("Cancel Scan")
        self.cancel_scan_button.setEnabled(False)
        self.folder_label = QLabel("No folder selected")
        self.library_guidance_label = QLabel("Choose a Mixed In Key processed folder to scan metadata.")
        self.recommendation_guidance_label = QLabel("Scan metadata before recommending a playlist.")
        self.export_guidance_label = QLabel(
            "Review recommendations before exporting; desktop export setup is intentionally out of scope."
        )
        self.safe_export_folder_button = QPushButton("Choose Safe Export Folder")
        self.safe_export_folder_label = QLabel(self._format_safe_export_folder_label())
        self.scan_progress_label = QLabel("Scan progress: idle")
        self.status_label = QLabel("Ready")
        self.tracks_table = QTableWidget(0, 7)
        self.tracks_table.setHorizontalHeaderLabels(["Title", "Artist", "BPM", "Key", "Energy", "Status", "Path"])
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(available_strategies())
        self.recommend_button = QPushButton("Recommend Playlist")
        self.recommendation_table = QTableWidget(0, 9)
        self.recommendation_table.setHorizontalHeaderLabels(
            ["Title", "Artist", "BPM", "Key", "Energy", "Strategy", "Path", "Transition Score", "Warnings"]
        )
        self.review_summary_label = QLabel(_EMPTY_REVIEW_SUMMARY)
        self.transition_review_table = QTableWidget(0, len(_TRANSITION_REVIEW_HEADERS))
        self.transition_review_table.setHorizontalHeaderLabels(_TRANSITION_REVIEW_HEADERS)

        self.folder_button.clicked.connect(self.choose_folder)
        self.scan_button.clicked.connect(self.scan_selected_folder)
        self.cancel_scan_button.clicked.connect(self.cancel_scan)
        self.recommend_button.clicked.connect(self.recommend_playlist)
        self.safe_export_folder_button.clicked.connect(self.choose_safe_export_folder)

        controls = QHBoxLayout()
        controls.addWidget(self.folder_button)
        controls.addWidget(self.scan_button)
        controls.addWidget(self.cancel_scan_button)

        recommendation_controls = QHBoxLayout()
        recommendation_controls.addWidget(QLabel("Strategy"))
        recommendation_controls.addWidget(self.strategy_combo)
        recommendation_controls.addWidget(self.recommend_button)

        layout = QVBoxLayout()
        layout.addLayout(controls)
        layout.addWidget(self.folder_label)
        layout.addWidget(self.library_guidance_label)
        layout.addWidget(self.scan_progress_label)
        layout.addWidget(self.tracks_table)
        layout.addWidget(self.recommendation_guidance_label)
        layout.addLayout(recommendation_controls)
        layout.addWidget(self.recommendation_table)
        layout.addWidget(self.review_summary_label)
        layout.addWidget(self.transition_review_table)
        layout.addWidget(self.export_guidance_label)
        layout.addWidget(self.safe_export_folder_button)
        layout.addWidget(self.safe_export_folder_label)
        layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    @classmethod
    def with_defaults(cls, db_path: Path, settings_path: Path | None = None) -> MainWindow:
        """Create a window wired to the default scan service, repository, and settings file."""
        from xfinaudio.config.settings_repository import SettingsRepository
        from xfinaudio.desktop.app import default_settings_path

        settings_repository = SettingsRepository(settings_path or default_settings_path())
        return cls(
            scan_service=MetadataScanService(),
            repository=TrackRepository(db_path),
            settings=settings_repository.load(),
            settings_repository=settings_repository,
        )

    def _format_safe_export_folder_label(self) -> str:
        """Return display text for the configured safe export folder."""
        folder = self.settings.export.safe_export_folder
        if folder is None:
            return "No safe export folder selected"
        return f"Safe export folder: {folder}"

    def choose_folder(self) -> None:
        """Open a folder picker and store the selected library folder."""
        folder = QFileDialog.getExistingDirectory(self, "Choose music folder")
        if folder:
            self.set_selected_folder(Path(folder))

    def set_selected_folder(self, folder: Path) -> None:
        """Set the current folder and update the display label."""
        self.selected_folder = folder
        self.folder_label.setText(str(folder))
        self.library_guidance_label.setText("Folder selected. Scan metadata to find complete Mixed In Key tracks.")
        self.status_label.setText("Folder selected")

    def choose_safe_export_folder(self) -> None:
        """Open a folder picker and store the selected safe export folder."""
        folder = QFileDialog.getExistingDirectory(self, "Choose safe export folder")
        if folder:
            self.set_safe_export_folder(Path(folder))

    def set_safe_export_folder(self, folder: Path) -> None:
        """Persist a safe export folder if it is not the selected audio folder."""
        if self.selected_folder is not None and folder == self.selected_folder:
            self.status_label.setText("Safe export folder must be outside the selected audio folder")
            return

        self.settings = self.settings.model_copy(update={"export": ExportSettings(safe_export_folder=folder)})
        if self.settings_repository is not None:
            self.settings_repository.save(self.settings)
        self.safe_export_folder_label.setText(self._format_safe_export_folder_label())
        self.status_label.setText("Safe export folder selected")

    def scan_selected_folder(self) -> None:
        """Scan the selected folder, persist records, and refresh table/status widgets."""
        if self.selected_folder is None:
            self.status_label.setText("Choose a folder before scanning")
            self.library_guidance_label.setText("Choose a Mixed In Key processed folder before scanning metadata.")
            return
        self._begin_scan_state()
        assert self.current_scan_cancellation_token is not None
        result = self.workflow_service.scan_folder(
            self.selected_folder,
            on_progress=self._show_scan_progress,
            cancellation_token=self.current_scan_cancellation_token,
        )
        self._end_scan_state()
        if result.cancelled:
            self.scanned_records = []
            self.tracks_table.setRowCount(0)
            self.clear_recommendation_review()
            self.status_label.setText("Scan canceled; no partial results were saved")
            self.recommendation_guidance_label.setText("Scan metadata before recommending a playlist.")
            return
        self.scanned_records = result.records
        self.show_tracks(result.records, result.complete_count, result.incomplete_count)
        self.recommendation_guidance_label.setText("Choose a strategy, then click Recommend Playlist.")

    def _begin_scan_state(self) -> None:
        """Prepare synchronous scan state and enable cooperative cancellation."""
        self.current_scan_cancellation_token = ScanCancellationToken()
        self.cancel_scan_button.setEnabled(True)
        self.scan_progress_label.setText("Scan progress: starting")
        self.status_label.setText("Scanning metadata")

    def _end_scan_state(self) -> None:
        """Clear synchronous scan state after scan completion or cancellation."""
        self.cancel_scan_button.setEnabled(False)
        self.current_scan_cancellation_token = None

    def _show_scan_progress(self, progress: ScanProgress) -> None:
        """Render scan progress from the workflow service."""
        self.scan_progress_label.setText(
            f"Scan progress: {progress.processed_count}/{progress.total_count} - {progress.current_path}"
        )

    def cancel_scan(self) -> None:
        """Request cooperative cancellation for the current synchronous scan."""
        if self.current_scan_cancellation_token is None:
            return
        self.current_scan_cancellation_token.cancel()
        self.cancel_scan_button.setEnabled(False)
        self.status_label.setText("Cancel requested; waiting for current file to finish")

    def show_tracks(
        self,
        records: list[TrackRecord],
        complete_count: int | None = None,
        incomplete_count: int | None = None,
    ) -> None:
        """Render scanned records in the desktop table."""
        self.tracks_table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            values = [
                record.title or "",
                record.artist or "",
                "" if record.bpm is None else f"{record.bpm:g}",
                record.camelot_key or "",
                "" if record.energy_level is None else str(record.energy_level),
                record.metadata_status,
                record.path,
            ]
            for column_index, value in enumerate(values):
                self.tracks_table.setItem(row_index, column_index, QTableWidgetItem(value))
        if complete_count is None:
            complete_count = sum(1 for record in records if record.metadata_status == "complete")
        if incomplete_count is None:
            incomplete_count = len(records) - complete_count
        self.status_label.setText(f"Scan complete: {complete_count} complete, {incomplete_count} incomplete")

    def recommend_playlist(self) -> None:
        """Generate and display a playlist recommendation from scanned records."""
        if not self.scanned_records:
            self.clear_recommendation_review()
            self.status_label.setText("Scan tracks before recommending")
            self.recommendation_guidance_label.setText("Scan metadata before recommending a playlist.")
            return
        strategy_name = self.strategy_combo.currentText()
        result = self.workflow_service.recommend(self.scanned_records, strategy_name)
        self.last_recommendation = result.recommendation
        self.last_playlist_explanation = result.explanation
        self.last_quality_report = result.quality_report
        self.show_recommendation(
            result.recommendation.ordered_tracks,
            result.recommendation.strategy.name,
            result.explanation,
        )
        self.review_summary_label.setText(format_quality_summary(result.quality_report))
        self.show_transition_review(result.explanation)
        recommended_count = len(result.recommendation.ordered_tracks)
        strategy_name = result.recommendation.strategy.name
        self.status_label.setText(f"Recommended {recommended_count} track(s) using {strategy_name}")
        self.export_guidance_label.setText(
            "Inspect the review table before exporting. "
            "Review scores and warnings before any safe export outside your audio library."
        )

    def show_recommendation(
        self,
        records: list[TrackRecord],
        strategy_name: str,
        explanation: PlaylistExplanation | None = None,
    ) -> None:
        """Render recommended records in the playlist table."""
        self.recommendation_table.setRowCount(len(records))
        transition_rows = explanation.transitions if explanation is not None else []
        for row_index, record in enumerate(records):
            transition = (
                transition_rows[row_index - 1] if row_index > 0 and row_index - 1 < len(transition_rows) else None
            )
            values = [
                record.title or "",
                record.artist or "",
                "" if record.bpm is None else f"{record.bpm:g}",
                record.camelot_key or "",
                "" if record.energy_level is None else str(record.energy_level),
                strategy_name,
                record.path,
                "" if transition is None else f"{transition.final_score:.3f}",
                ""
                if transition is None
                else "; ".join(format_recommendation_warning(warning) for warning in transition.warnings),
            ]
            for column_index, value in enumerate(values):
                self.recommendation_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def clear_recommendation_review(self) -> None:
        """Reset recommendation review widgets to their empty state."""
        self.review_summary_label.setText(_EMPTY_REVIEW_SUMMARY)
        self.transition_review_table.setRowCount(0)

    def show_transition_review(self, explanation: PlaylistExplanation) -> None:
        """Render transition component scores and warnings in the review table."""
        self.transition_review_table.setRowCount(len(explanation.transitions))
        for row_index, transition in enumerate(explanation.transitions):
            values = [
                str(transition.order),
                _track_review_name(transition.left),
                _track_review_name(transition.right),
                _format_review_score(_component_score(transition, "key_score", "harmonic")),
                _format_review_score(_component_score(transition, "bpm_score", "bpm")),
                _format_review_score(_component_score(transition, "energy_score", "energy")),
                _format_review_score(_component_score(transition, "tag_score", "tags")),
                _format_review_score(transition.final_score),
                "; ".join(format_recommendation_warning(warning) for warning in transition.warnings),
            ]
            for column_index, value in enumerate(values):
                self.transition_review_table.setItem(row_index, column_index, QTableWidgetItem(value))
