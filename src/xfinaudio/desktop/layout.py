"""Responsive layout helpers for the desktop shell."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.responsive import ResponsiveLayout
from xfinaudio.desktop.status_bar import StatusBar
from xfinaudio.desktop.workflow_stack import WorkflowStack
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls

_SIDEBAR_WIDTH_WIDE = 180
_SIDEBAR_WIDTH_NARROW = 120
_NARROW_BREAKPOINT = 900
_TRACK_TITLE_COLUMN = 0
_TRACK_STATUS_COLUMN = 9
_TRACK_PATH_COLUMN = 11
_RECOMMENDATION_READY_GUIDANCE = QCoreApplication.translate(
    "MainWindow",
    "Selected row starts the playlist; multiple selected rows set the opening order. "
    "Up to 25 candidates are used for interactive speed. Choose a strategy, then click Recommend Playlist.",
)


def responsive_sidebar_width(window_width: int) -> int:
    """Map a window width to the sidebar width: wide above the breakpoint, narrow below."""
    return _SIDEBAR_WIDTH_WIDE if window_width >= _NARROW_BREAKPOINT else _SIDEBAR_WIDTH_NARROW


def build_main_layout(self: Any) -> None:
    workflow_labels = [
        self.tr("Library"),
        self.tr("Build Playlist"),
        self.tr("Review Mix"),
        self.tr("Export to Serato"),
        self.tr("My Playlists"),
        self.tr("Metadata Worklist"),
        self.tr("Live Assistant"),
    ]
    self._workflow_labels = workflow_labels
    self.workflow_sidebar = QListWidget()
    self.workflow_sidebar.setObjectName("workflowSidebar")
    self.workflow_sidebar.setAccessibleName(self.tr("Workflow navigation"))
    self.workflow_sidebar.setFixedWidth(_SIDEBAR_WIDTH_WIDE)
    self.workflow_sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    for label in workflow_labels:
        item = QListWidgetItem(label)
        item.setData(Qt.ItemDataRole.AccessibleTextRole, label)
        item.setToolTip(label)
        self.workflow_sidebar.addItem(item)

    self.workflow_tabs = WorkflowStack(workflow_labels)
    self.workflow_tabs.addWidget(self._library_screen)
    self.workflow_tabs.addWidget(self._build_screen)
    self.workflow_tabs.addWidget(self._review_screen)
    self.workflow_tabs.addWidget(self._export_screen)
    self.workflow_tabs.addWidget(self._playlists_screen)
    self.workflow_tabs.addWidget(self._metadata_screen)
    self.workflow_tabs.addWidget(self._live_assistant_screen)
    self._current_tab_index = self.workflow_tabs.currentIndex()
    self.workflow_tabs.currentChanged.connect(self._on_tab_changed)
    self.workflow_tabs.currentChanged.connect(self.workflow_sidebar.setCurrentRow)
    self.workflow_sidebar.currentRowChanged.connect(self._on_sidebar_row_changed)
    self.workflow_sidebar.setCurrentRow(0)

    workflow_layout = QHBoxLayout()
    workflow_layout.setContentsMargins(0, 0, 0, 0)
    workflow_layout.setSpacing(10)
    sidebar_panel = QWidget()
    sidebar_panel.setObjectName("workflowSidebarPanel")
    sidebar_panel.setFixedWidth(_SIDEBAR_WIDTH_WIDE)
    sidebar_layout = QVBoxLayout()
    sidebar_layout.setContentsMargins(0, 0, 0, 0)
    sidebar_layout.setSpacing(0)
    sidebar_layout.addWidget(self.workflow_sidebar, 0)
    sidebar_layout.addStretch(1)
    sidebar_panel.setLayout(sidebar_layout)
    self._sidebar_panel = sidebar_panel
    self._responsive_layout = ResponsiveLayout(
        self._sidebar_panel, self.workflow_sidebar, self._workflow_labels, responsive_sidebar_width
    )
    workflow_layout.addWidget(sidebar_panel)
    workflow_layout.addWidget(self.workflow_tabs, 1)

    layout = QVBoxLayout()
    layout.addLayout(workflow_layout, 1)
    layout.addWidget(self.status_label)
    status_controls = QHBoxLayout()
    status_controls.addWidget(self.status_bar_toggle)
    status_controls.addWidget(self.status_bar, 1)
    layout.addLayout(status_controls)
    self._status_controls_widgets = (self.status_bar_toggle, self.status_bar)
    self._responsive_layout.set_full_screen_context(self, self._status_controls_widgets)
    self._apply_compact_mac_layout(
        layout,
        status_controls,
    )

    container = QWidget()
    container.setLayout(layout)
    self.setCentralWidget(container)


def build_main_widgets(self: Any) -> None:
    self.setWindowTitle(self.tr("XfinAudio"))
    self.folder_label = QLabel(self.tr("Library: none"))
    self.library_guidance_label = QLabel(self.tr("Choose a folder to scan metadata."))
    self.recommendation_guidance_label = QLabel(self.tr("Scan metadata before recommending a playlist."))
    self.scan_progress_label = QLabel(self.tr("Scan: idle"))
    self.status_bar = StatusBar(self.folder_label, self.library_guidance_label, self.scan_progress_label)
    self.status_bar.hide()
    self.status_bar_toggle = QPushButton(self.tr("Status"))
    self.status_bar_toggle.setCheckable(True)
    self.status_label = QLabel(self.tr("Ready"))
    self.library_decision_label = QLabel(self.tr("DJ Decision Point: choose source, filters, and the track anchor."))
    self.metadata_decision_label = QLabel(
        self.tr("DJ Decision Point: complete missing metadata, then refresh the library.")
    )
    self._library_screen.tracks_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    self._library_screen.tracks_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    self._library_screen.scan_button.setToolTip(self.tr("Scan Metadata (Ctrl+Shift+S)"))
    self._library_screen.missing_column_button.setToolTip(self.tr("Toggle Missing column (Ctrl+M)"))
    self._build_screen.recommend_button.setToolTip(self.tr("Recommend Playlist (Ctrl+R)"))
    self._review_screen.remove_track_button.setToolTip(self.tr("Remove from Playlist (Delete)"))
    self._export_screen.export_button.setToolTip(self.tr("Export to Serato (Ctrl+E)"))
    self.folder_label.setWordWrap(False)
    self.folder_label.setMaximumWidth(220)
    self.library_guidance_label.setWordWrap(False)
    self.library_guidance_label.setMaximumWidth(720)
    self.scan_progress_label.setWordWrap(False)
    self.scan_progress_label.setMaximumWidth(140)
    self.recommendation_guidance_label.setWordWrap(True)
    for label in (self.folder_label, self.library_guidance_label, self.scan_progress_label):
        label.setMaximumHeight(24)
    self._export_screen.safe_export_folder_label.setText(self._format_safe_export_folder_label())
    self._build_undo_toolbar()


def wire_main_scan_service(self: Any) -> None:
    self._scan_service.set_state_accessors(
        selected_folder=lambda: self.selected_folder,
        scanned_records=lambda: self.scanned_records,
        set_scanned_records=lambda records: setattr(self, "scanned_records", records),
        state=self._state,
    )
    self._scan_service.set_ui(
        library_screen=self._library_screen,
        build_screen=self._build_screen,
        status_label=self.status_label,
        scan_progress_label=self.scan_progress_label,
        library_guidance_label=self.library_guidance_label,
        recommendation_guidance_label=self.recommendation_guidance_label,
        tr=self.tr,
    )
    self._scan_service.set_actions(
        sync_state=self._sync_state,
        show_tracks=self.show_tracks,
        clear_scan_dependent_state=self._clear_scan_dependent_state,
        refresh_idle_action_state=self._refresh_idle_action_state,
        cancel_spectral_completion_worker=self._cancel_spectral_completion_worker,
        show_status_bar=self.show_status_bar,
    )


def wire_main_recommendation_service(self: Any) -> None:
    self._recommendation_service.set_state_accessors(
        scanned_records=lambda: self.scanned_records,
        set_is_recommending=lambda value: setattr(self, "_is_recommending", value),
        state=self._state,
    )
    self._recommendation_service.set_ui(
        build_screen=self._build_screen,
        review_screen=self._review_screen,
        export_screen=self._export_screen,
        library_screen=self._library_screen,
        status_label=self.status_label,
        recommendation_guidance_label=self.recommendation_guidance_label,
        tr=self.tr,
    )
    self._recommendation_service.set_actions(
        sync_state=self._sync_state,
        clear_recommendation_review=self.clear_recommendation_review,
        show_recommendation=self.show_recommendation,
        show_transition_review=self.show_transition_review,
        selected_track_controls=self._selected_track_controls,
        desktop_recommendation_records=self._desktop_recommendation_records,
        set_recommendation_sections_expanded=self._set_recommendation_sections_expanded,
        set_applied_copilot_variant=self._set_applied_copilot_variant,
        show_dj_readiness=self._show_dj_readiness,
        refresh_idle_action_state=self._refresh_idle_action_state,
    )


def apply_main_song_filter(self: Any, query: str | None = None, *, clear_selection: bool = False) -> None:
    search_query = (self._library_screen.search_input.text() if query is None else query).strip().casefold()
    if clear_selection and search_query != self._active_song_search_query:
        self._library_screen.tracks_table.clearSelection()
    self._active_song_search_query = search_query
    status_filter = self._selected_metadata_status_filter()
    missing_filter = self._selected_missing_metadata_filter()
    for row_index in range(self._library_screen.tracks_table.rowCount()):
        title_item = self._library_screen.tracks_table.item(row_index, _TRACK_TITLE_COLUMN)
        title = "" if title_item is None else title_item.text().casefold()
        status_item = self._library_screen.tracks_table.item(row_index, _TRACK_STATUS_COLUMN)
        status = "" if status_item is None else status_item.text()
        path_item = self._library_screen.tracks_table.item(row_index, _TRACK_PATH_COLUMN)
        path = "" if path_item is None else path_item.text()
        record = self._records_by_path.get(path)
        title_mismatch = bool(search_query) and search_query not in title
        status_mismatch = status_filter is not None and status != status_filter
        missing_mismatch = missing_filter is not None and (
            record is None or missing_filter not in record.missing_required_fields
        )
        self._library_screen.tracks_table.setRowHidden(
            row_index,
            title_mismatch or status_mismatch or missing_mismatch,
        )
    self._refresh_idle_action_state()


def restore_main_persisted_tracks(self: Any, records: list[TrackRecord]) -> None:
    if not records:
        self._refresh_idle_action_state()
        return
    self.scanned_records = records
    complete_count = sum(1 for record in records if record.metadata_status == "complete")
    incomplete_count = len(records) - complete_count
    self._populate_track_table(records)
    if self.selected_folder is None:
        self.folder_label.setText(self.tr("Library: saved"))
        self.folder_label.setToolTip(self.tr("Saved library loaded; no scan folder selected."))
        self.library_guidance_label.setText(self.tr("Use filters/search, select a complete track, then recommend."))
        self.library_guidance_label.setToolTip(
            self.tr("Showing saved library from the app database. Choose a folder to re-scan or update metadata.")
        )
    else:
        self.folder_label.setText(self.tr("Library: saved folder"))
        self.folder_label.setToolTip(self.tr("Saved library loaded: {0}").format(self.selected_folder))
        self.library_guidance_label.setText(self.tr("Use filters/search, select a complete track, then recommend."))
        self.library_guidance_label.setToolTip(
            self.tr("Saved library loaded. Click Scan Metadata to refresh metadata from the last folder.")
        )
    self.recommendation_guidance_label.setText(_RECOMMENDATION_READY_GUIDANCE)
    self.status_label.setText(
        self.tr("Loaded saved library: {0} complete, {1} incomplete").format(complete_count, incomplete_count)
    )
    self._refresh_idle_action_state()
    self._sync_state()
    self._start_spectral_completion_worker(records)


def clear_main_scan_dependent_state(self: Any) -> None:
    self.scanned_records = []
    self._records_by_path = {}
    self.last_recommendation = None
    self.last_playlist_explanation = None
    self.last_quality_report = None
    self.last_dj_readiness_report = None
    self.last_prep_copilot_plan = None
    self._set_applied_copilot_variant(None)
    self._library_screen.tracks_table.setRowCount(0)
    self._library_screen.search_input.clear()
    self._review_screen.recommendation_table.setRowCount(0)
    self._set_recommendation_sections_expanded(False)
    self.clear_recommendation_review()
    self._export_screen.export_guidance_label.setText(
        self.tr(
            "Review recommendations before exporting. Serato export is enabled only after a recommendation is ready."
        )
    )

    self._sync_state()


def selected_main_track_controls(self: Any) -> DJControls | None:
    records_by_path = {record.path: record for record in self.scanned_records}

    if self._library_selected_paths:
        selected_records: list[TrackRecord] = []
        seen_paths: set[str] = set()
        for path in self._library_selected_paths:
            record = records_by_path.get(path)
            if record is None or record.metadata_status != "complete" or path in seen_paths:
                continue
            selected_records.append(record)
            seen_paths.add(path)
        if selected_records:
            if len(selected_records) == 1:
                return DJControls(
                    start_path=selected_records[0].path,
                    excluded_paths=self._state.excluded_paths,
                    locked_paths=self._state.locked_paths,
                )
            return DJControls(
                manual_order_paths=[r.path for r in selected_records],
                excluded_paths=self._state.excluded_paths,
                locked_paths=self._state.locked_paths,
            )

    selected_rows = sorted({index.row() for index in self._library_screen.tracks_table.selectedIndexes()})
    selected_records = []
    seen_paths = set()
    for row in selected_rows:
        if self._library_screen.tracks_table.isRowHidden(row):
            continue
        path_item = self._library_screen.tracks_table.item(row, _TRACK_PATH_COLUMN)
        if path_item is None:
            continue
        record = records_by_path.get(path_item.text())
        if record is None or record.metadata_status != "complete" or record.path in seen_paths:
            continue
        selected_records.append(record)
        seen_paths.add(record.path)
    if not selected_records:
        return None
    if len(selected_records) == 1:
        return DJControls(
            start_path=selected_records[0].path,
            excluded_paths=self._state.excluded_paths,
            locked_paths=self._state.locked_paths,
        )
    return DJControls(
        manual_order_paths=[record.path for record in selected_records],
        excluded_paths=self._state.excluded_paths,
        locked_paths=self._state.locked_paths,
    )
