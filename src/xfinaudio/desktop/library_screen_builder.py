"""Cohesive widget construction for LibraryScreen."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)

_CHECKED_FILTER_BUTTON_STYLE = "QPushButton:checked { background: #00d4ff; color: #061018; border-color: #00d4ff; }"


def build_library_screen_ui(screen: Any, columns: list[str], missing_column: int) -> None:
    screen._filter_query = ""
    screen._missing_column_visible = False

    layout = QVBoxLayout(screen)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)

    # Top controls row
    controls = QHBoxLayout()
    screen.folder_button = QPushButton(screen.tr("Choose Folder"))
    screen.scan_button = QPushButton(screen.tr("Scan Metadata"))
    screen.scan_button.setObjectName("primaryAction")
    screen.scan_button.setMinimumHeight(36)
    screen.cancel_button = QPushButton(screen.tr("Cancel Scan"))
    screen.cancel_button.setObjectName("secondaryAction")
    screen.cancel_button.setMaximumHeight(26)
    screen.missing_column_button = QPushButton(screen.tr("Show Missing"))
    screen.cancel_button.setEnabled(False)
    controls.addWidget(screen.folder_button)
    controls.addWidget(screen.scan_button)
    screen.scan_progress_bar = QProgressBar()
    screen.scan_progress_bar.setRange(0, 100)
    screen.scan_progress_bar.setTextVisible(False)
    screen.scan_progress_bar.setVisible(False)
    screen.scan_progress_label = QLabel("")
    screen.scan_progress_label.setVisible(False)
    controls.addWidget(screen.scan_progress_bar)
    controls.addWidget(screen.scan_progress_label)
    controls.addWidget(screen.cancel_button)
    controls.addWidget(screen.missing_column_button)
    controls.addStretch()
    layout.addLayout(controls)

    # Scan settings review
    screen.scan_settings_label = QLabel()
    screen.scan_settings_label.setWordWrap(True)
    layout.addWidget(screen.scan_settings_label)

    # Status
    screen.status_label = QLabel()
    layout.addWidget(screen.status_label)

    # Search
    screen.search_input = QLineEdit()
    screen.search_input.setPlaceholderText(screen.tr("Search songs"))
    screen.search_input.setMinimumWidth(160)
    screen.search_input.setMaximumWidth(220)
    layout.addWidget(screen.search_input)

    screen.quick_filter_layout = QHBoxLayout()
    (
        screen.complete_filter_button,
        screen.incomplete_filter_button,
        screen.missing_bpm_filter_button,
        screen.missing_key_filter_button,
        screen.missing_energy_filter_button,
    ) = (
        QPushButton(screen.tr(label))
        for label in ("Complete", "Incomplete", "Missing BPM", "Missing Key", "Missing Energy")
    )
    screen.quick_filter_buttons = (
        screen.complete_filter_button,
        screen.incomplete_filter_button,
        screen.missing_bpm_filter_button,
        screen.missing_key_filter_button,
        screen.missing_energy_filter_button,
    )
    screen.clear_filters_button = QPushButton(screen.tr("Clear Filters"))
    screen.active_filter_count_label = QLabel(screen.tr("0 active"))
    for button in screen.quick_filter_buttons:
        button.setCheckable(True)
        button.setStyleSheet(_CHECKED_FILTER_BUTTON_STYLE)
        screen.quick_filter_layout.addWidget(button)
    # Hide Duplicates is deliberately NOT part of quick_filter_buttons — it must not
    # participate in the Complete/Incomplete vs Missing-* mutual-exclusion logic.
    screen.hide_duplicates_button = QPushButton(screen.tr("Hide Duplicates"))
    screen.hide_duplicates_button.setCheckable(True)
    screen.hide_duplicates_button.setStyleSheet(_CHECKED_FILTER_BUTTON_STYLE)
    screen.quick_filter_layout.addWidget(screen.hide_duplicates_button)
    screen.quick_filter_layout.addWidget(screen.clear_filters_button)
    screen.quick_filter_layout.addWidget(screen.active_filter_count_label)
    screen.duplicate_count_label = QLabel("")
    screen.quick_filter_layout.addWidget(screen.duplicate_count_label)
    screen.quick_filter_layout.addStretch()
    layout.addLayout(screen.quick_filter_layout)

    # Section divider between controls and table
    screen.section_divider = QFrame()
    screen.section_divider.setObjectName("sectionDivider")
    screen.section_divider.setFrameShape(QFrame.Shape.HLine)
    layout.addWidget(screen.section_divider)

    # Empty-state guidance (no library / no tracks)
    screen.empty_state_label = QLabel()
    screen.empty_state_label.setObjectName("guidanceLabel")
    screen.empty_state_label.setWordWrap(True)
    layout.addWidget(screen.empty_state_label)

    # Table
    screen.tracks_table = QTableWidget(0, len(columns))
    screen.tracks_table.setHorizontalHeaderLabels([screen.tr(c) for c in columns])
    header = screen.tracks_table.horizontalHeader()
    # Header tooltips explain each column to novice DJs.
    _HEADER_TOOLTIPS = [
        "Track title from audio metadata",
        "Artist or performer name",
        "Beats per minute — tempo of the track",
        "Musical key in Camelot notation (e.g. 8A, 11B)",
        "Energy level from 1 (calm) to 10 (intense)",
        "Track duration in minutes and seconds",
        "Spectral color profile (RED = bass, GREEN = mids, BLUE = highs)",
        "Metadata fields still missing for this track",
        "Primary genre detected by Mixed In Key",
        "Metadata completeness: complete or incomplete",
        "Click to preview the track",
        "Full file path on disk",
    ]
    for col, tip in enumerate(_HEADER_TOOLTIPS):
        header_item = screen.tracks_table.horizontalHeaderItem(col)
        if header_item is not None:
            header_item.setToolTip(screen.tr(tip))
    # Allow users to reorder columns by dragging headers.
    header.setSectionsMovable(True)
    # Stretch all columns by default so the table fills available width.
    header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    # Narrow data columns only take the space they need.
    for col in (2, 3, 4, 5, 6, 9, 10):  # BPM, Key, Energy, Duration, Color, Status, Preview
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
    screen.tracks_table.setAlternatingRowColors(True)
    screen.tracks_table.setSelectionBehavior(screen.tracks_table.SelectionBehavior.SelectRows)
    screen.tracks_table.verticalHeader().setVisible(False)
    # Hide Path column by default — full paths are rarely useful at a glance.
    screen.tracks_table.setColumnHidden(len(columns) - 1, True)
    # Hide Missing column by default — useful on demand, but cramped during browsing.
    screen.tracks_table.setColumnHidden(missing_column, True)
    layout.addWidget(screen.tracks_table)

    # Bottom row
    bottom = QHBoxLayout()
    screen.settings_button = QPushButton(screen.tr("⚙ Settings"))
    screen.settings_button.setObjectName("secondaryAction")
    screen.settings_button.setMaximumHeight(26)
    screen.help_button = QPushButton(screen.tr("What's this?"))
    screen.help_button.setObjectName("secondaryAction")
    screen.help_button.setMaximumHeight(26)
    screen.tour_button = QPushButton(screen.tr("Tour"))
    screen.tour_button.setObjectName("secondaryAction")
    screen.tour_button.setMaximumHeight(26)
    screen.proceed_button = QPushButton(screen.tr("Build Playlist →"))
    bottom.addWidget(screen.settings_button)
    bottom.addWidget(screen.help_button)
    bottom.addWidget(screen.tour_button)
    bottom.addStretch()
    bottom.addWidget(screen.proceed_button)
    layout.addLayout(bottom)

    screen._setup_button_tooltips()
    screen._setup_accessibility()
    screen._setup_tab_order()
