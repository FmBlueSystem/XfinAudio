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
from xfinaudio.desktop.undo_toolbar import UndoToolbar
from xfinaudio.desktop.visual_design import apply_compact_mac_layout
from xfinaudio.desktop.workflow_stack import WorkflowStack

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


"""Responsive primitives extracted from the legacy layout facade."""

_SIDEBAR_WIDTH_WIDE = 180
_SIDEBAR_WIDTH_NARROW = 120
_NARROW_BREAKPOINT = 900


def responsive_sidebar_width(window_width: int) -> int:
    return _SIDEBAR_WIDTH_WIDE if window_width >= _NARROW_BREAKPOINT else _SIDEBAR_WIDTH_NARROW


def build_main_window_layout(self: Any) -> None:
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
    apply_compact_mac_layout(self, layout, status_controls)

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
    self._export_screen.safe_export_folder_label.setText(self._settings_controller.format_safe_export_folder_label())
    self._undo_toolbar = UndoToolbar(self._undo_manager, self)
    self.addToolBar(self._undo_toolbar.toolbar)
    self.undo_button = self._undo_toolbar.undo_button
    self.redo_button = self._undo_toolbar.redo_button
    self.undo_history_menu = self._undo_toolbar.undo_history_menu
