"""BuildScreen — thin QWidget that renders BuildViewModel data."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.build_view_model import BuildViewModel, CopilotVariantRow
from xfinaudio.desktop.scan_service import progress_percent, progress_status_text

_READINESS_STATUS_LABELS = {"ready": "Ready", "needs_review": "Needs Review", "blocked": "Blocked"}
_READINESS_STATUS_COLORS = {"ready": "#1fd16a", "needs_review": "#ffb000", "blocked": "#ff4d4f"}

_COPILOT_COLUMNS = ["Variant", "Description", "Tracks", "Readiness"]
_COPILOT_HEADER_TOOLTIPS = [
    "Name of this Prep Copilot playlist variant",
    "How this variant was assembled and what it emphasizes",
    "Number of tracks in this variant",
    "DJ readiness: Ready, Needs Review, or Blocked",
]


class BuildScreen(QWidget):
    """Displays strategy selection and Prep Copilot controls."""

    recommend_requested = Signal(str, list)
    spectral_cohesion_changed = Signal(int)
    copilot_generate_requested = Signal()
    copilot_variant_applied = Signal(int)
    back_requested = Signal()
    exclude_requested = Signal()
    lock_requested = Signal()
    clear_constraints_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._last_vm: BuildViewModel | None = None
        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Strategy row
        strategy_row = QHBoxLayout()
        self.strategy_combo = QComboBox()
        self.recommend_button = QPushButton(self.tr("Recommend Playlist"))
        self.recommend_button.setObjectName("primaryAction")
        self.recommend_button.setMinimumHeight(36)
        self.recommend_button.setEnabled(False)
        self.recommend_progress_bar = QProgressBar()
        self.recommend_progress_bar.setRange(0, 100)
        self.recommend_progress_bar.setTextVisible(False)
        self.recommend_progress_bar.setVisible(False)
        self.recommend_progress_label = QLabel("")
        self.recommend_progress_label.setVisible(False)
        strategy_row.addWidget(self.strategy_combo)
        strategy_row.addWidget(self.recommend_button)
        strategy_row.addWidget(self.recommend_progress_bar)
        strategy_row.addWidget(self.recommend_progress_label)
        strategy_row.addStretch()
        layout.addLayout(strategy_row)

        # Guidance labels — keep compact so the table gets vertical space.
        self.anchor_label = QLabel()
        self.anchor_label.setWordWrap(True)
        self.anchor_label.setMaximumHeight(40)
        layout.addWidget(self.anchor_label)

        self.strategy_explanation_label = QLabel()
        self.strategy_explanation_label.setWordWrap(True)
        self.strategy_explanation_label.setMaximumHeight(36)
        layout.addWidget(self.strategy_explanation_label)

        # Spectral cohesion slider
        cohesion_row = QHBoxLayout()
        cohesion_row.addWidget(QLabel(self.tr("Spectral Cohesion")))
        self.spectral_cohesion_slider = QSlider()
        self.spectral_cohesion_slider.setOrientation(Qt.Orientation.Horizontal)
        self.spectral_cohesion_slider.setRange(0, 100)
        self.spectral_cohesion_slider.setValue(50)
        self.spectral_cohesion_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.spectral_cohesion_slider.setTickInterval(25)
        self.spectral_cohesion_slider.setAccessibleName(self.tr("Spectral cohesion"))
        self.spectral_cohesion_value_label = QLabel("50%")
        self.spectral_cohesion_value_label.setMinimumWidth(40)
        cohesion_row.addWidget(self.spectral_cohesion_slider, 1)
        cohesion_row.addWidget(self.spectral_cohesion_value_label)
        cohesion_row.addStretch()
        layout.addLayout(cohesion_row)

        self.recommendation_vs_copilot_label = QLabel()
        self.recommendation_vs_copilot_label.setWordWrap(True)
        self.recommendation_vs_copilot_label.setMaximumHeight(36)
        layout.addWidget(self.recommendation_vs_copilot_label)

        self.constraint_explanation_label = QLabel()
        self.constraint_explanation_label.setWordWrap(True)
        self.constraint_explanation_label.setMaximumHeight(36)
        layout.addWidget(self.constraint_explanation_label)

        self.recommendation_summary_label = QLabel()
        self.recommendation_summary_label.setWordWrap(True)
        self.recommendation_summary_label.setMaximumHeight(36)
        layout.addWidget(self.recommendation_summary_label)

        # Constraints row
        constraints_row = QHBoxLayout()
        self.exclude_button = QPushButton(self.tr("Exclude Selected"))
        self.lock_button = QPushButton(self.tr("Lock Selected"))
        self.clear_constraints_button = QPushButton(self.tr("Clear Constraints"))
        self.clear_constraints_button.setEnabled(False)
        self.constraints_label = QLabel("")
        constraints_row.addWidget(self.exclude_button)
        constraints_row.addWidget(self.lock_button)
        constraints_row.addWidget(self.clear_constraints_button)
        constraints_row.addWidget(self.constraints_label)
        constraints_row.addStretch()
        layout.addLayout(constraints_row)

        # Copilot section
        copilot_row = QHBoxLayout()
        self.target_count_input = QSpinBox()
        self.target_count_input.setRange(2, 100)
        self.target_count_input.setValue(25)
        self.genre_focus_input = QLineEdit()
        self.genre_focus_input.setPlaceholderText(self.tr("Genre focus"))
        self.copilot_button = QPushButton(self.tr("Generate Prep Copilot"))
        self.variant_label = QLabel()
        copilot_row.addWidget(QLabel(self.tr("Set Tracks")))
        copilot_row.addWidget(self.target_count_input)
        copilot_row.addWidget(self.genre_focus_input)
        copilot_row.addWidget(self.copilot_button)
        copilot_row.addWidget(self.variant_label)
        copilot_row.addStretch()
        layout.addLayout(copilot_row)

        # Section divider between controls and copilot table
        self.section_divider = QFrame()
        self.section_divider.setObjectName("sectionDivider")
        self.section_divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(self.section_divider)

        # Empty-state guidance (no recommendation yet)
        self.empty_state_label = QLabel()
        self.empty_state_label.setObjectName("guidanceLabel")
        self.empty_state_label.setWordWrap(True)
        layout.addWidget(self.empty_state_label)

        # Copilot variants table — expanding so it absorbs spare vertical space.
        self.copilot_table = QTableWidget(0, len(_COPILOT_COLUMNS))
        self.copilot_table.setHorizontalHeaderLabels([self.tr(c) for c in _COPILOT_COLUMNS])
        for col, tip in enumerate(_COPILOT_HEADER_TOOLTIPS):
            header_item = self.copilot_table.horizontalHeaderItem(col)
            if header_item is not None:
                header_item.setToolTip(self.tr(tip))
        self.copilot_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.copilot_table.setAlternatingRowColors(True)
        self.copilot_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.copilot_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.copilot_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.copilot_table, 1)

        # Applied variant badge (set imperatively by main_window)
        self.applied_copilot_variant_label = QLabel(self.tr("Applied Variant: none"))
        self.applied_copilot_variant_label.setToolTip(self.tr("No Prep Copilot variant is currently applied."))
        layout.addWidget(self.applied_copilot_variant_label)

        # Apply variant button
        self.apply_variant_button = QPushButton(self.tr("Apply Selected Variant"))
        layout.addWidget(self.apply_variant_button)

        # Push nav to bottom; spare space goes to the copilot table.
        layout.addStretch(1)

        # Bottom navigation
        nav = QHBoxLayout()
        self.back_button = QPushButton(self.tr("← Library"))
        self.back_button.setObjectName("secondaryAction")
        self.back_button.setMaximumHeight(26)
        self.proceed_button = QPushButton(self.tr("Review →"))
        nav.addWidget(self.back_button)
        nav.addStretch()
        nav.addWidget(self.proceed_button)
        layout.addLayout(nav)

        self._setup_button_tooltips()
        self._setup_accessibility()
        self._setup_tab_order()

    def _setup_button_tooltips(self) -> None:
        """Explain every button so users understand each control (R1)."""
        tips = {
            self.recommend_button: "Generate a playlist using the selected strategy",
            self.exclude_button: "Exclude the selected tracks from recommendations",
            self.lock_button: "Lock the selected tracks so they always appear",
            self.clear_constraints_button: "Remove all exclude and lock constraints",
            self.copilot_button: "Generate several Prep Copilot playlist variants",
            self.apply_variant_button: "Apply the selected Prep Copilot variant",
            self.back_button: "Return to the Library screen",
            self.proceed_button: "Move on to review the recommended playlist",
        }
        for button, tip in tips.items():
            button.setToolTip(self.tr(tip))

    def _setup_accessibility(self) -> None:
        """Set accessible names for screen readers."""
        self.strategy_combo.setAccessibleName(self.tr("Recommendation strategy"))
        self.recommend_button.setAccessibleName(self.tr("Recommend playlist"))
        self.spectral_cohesion_slider.setAccessibleName(self.tr("Spectral cohesion"))
        self.exclude_button.setAccessibleName(self.tr("Exclude selected tracks"))
        self.lock_button.setAccessibleName(self.tr("Lock selected tracks"))
        self.clear_constraints_button.setAccessibleName(self.tr("Clear constraints"))
        self.target_count_input.setAccessibleName(self.tr("Target track count"))
        self.genre_focus_input.setAccessibleName(self.tr("Genre focus"))
        self.copilot_button.setAccessibleName(self.tr("Generate Prep Copilot variants"))
        self.copilot_table.setAccessibleName(self.tr("Prep Copilot variants"))
        self.apply_variant_button.setAccessibleName(self.tr("Apply selected Prep Copilot variant"))
        self.back_button.setAccessibleName(self.tr("Back to library"))
        self.proceed_button.setAccessibleName(self.tr("Proceed to review"))

    def _setup_tab_order(self) -> None:
        """Define a logical keyboard tab order across primary controls."""
        self.setTabOrder(self.strategy_combo, self.recommend_button)
        self.setTabOrder(self.recommend_button, self.spectral_cohesion_slider)
        self.setTabOrder(self.spectral_cohesion_slider, self.exclude_button)
        self.setTabOrder(self.exclude_button, self.lock_button)
        self.setTabOrder(self.lock_button, self.clear_constraints_button)
        self.setTabOrder(self.clear_constraints_button, self.target_count_input)
        self.setTabOrder(self.target_count_input, self.genre_focus_input)
        self.setTabOrder(self.genre_focus_input, self.copilot_button)
        self.setTabOrder(self.copilot_button, self.copilot_table)
        self.setTabOrder(self.copilot_table, self.apply_variant_button)
        self.setTabOrder(self.apply_variant_button, self.back_button)
        self.setTabOrder(self.back_button, self.proceed_button)

    def _connect_signals(self) -> None:
        self.back_button.clicked.connect(self.back_requested)
        self.copilot_button.clicked.connect(self.copilot_generate_requested)
        self.apply_variant_button.clicked.connect(self._on_apply_variant)
        self.recommend_button.clicked.connect(self._on_recommend)
        self.exclude_button.clicked.connect(self.exclude_requested)
        self.lock_button.clicked.connect(self.lock_requested)
        self.clear_constraints_button.clicked.connect(self.clear_constraints_requested)
        self.spectral_cohesion_slider.valueChanged.connect(self._on_spectral_cohesion_changed)
        self.strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)

    def connect_signals(self, window: Any) -> None:
        self.copilot_table.itemDoubleClicked.connect(window._apply_prep_copilot_item)
        self.recommend_requested.connect(window._on_recommend_requested)
        self.spectral_cohesion_changed.connect(window._settings_controller.on_spectral_cohesion_changed)
        self.copilot_generate_requested.connect(window.generate_prep_copilot)
        self.copilot_variant_applied.connect(window._on_copilot_variant_applied)
        self.back_requested.connect(lambda: window.workflow_tabs.setCurrentIndex(0))
        self.proceed_button.clicked.connect(lambda: window.workflow_tabs.setCurrentIndex(2))
        self.exclude_requested.connect(window._library_controller.on_exclude_requested)
        self.lock_requested.connect(window._library_controller.on_lock_requested)
        self.clear_constraints_requested.connect(window._library_controller.on_clear_constraints)

    def _on_spectral_cohesion_changed(self, value: int) -> None:
        self.spectral_cohesion_value_label.setText(f"{value}%")
        self.spectral_cohesion_changed.emit(value)

    def spectral_cohesion_value(self) -> int:
        """Return the current spectral cohesion slider value (0-100)."""
        return self.spectral_cohesion_slider.value()

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, vm: BuildViewModel, state: AppState, lightweight: bool = False) -> None:
        """Update all widgets from ViewModel data.

        Args:
            lightweight: If True, skip expensive copilot table population
                        (used for non-visible tabs during state sync).
        """
        self._last_vm = vm

        # Populate strategy combo (only if empty to avoid clearing user selection)
        if self.strategy_combo.count() == 0:
            for option in vm.available_strategies():
                self.strategy_combo.addItem(option.display_name, option.name)

        # recommend_button enabled state is managed by MainWindow._refresh_idle_action_state
        self.copilot_button.setEnabled(vm.copilot_button_enabled(state))
        self._render_recommend_progress(state)
        no_recommendation = state.last_recommendation is None
        self.empty_state_label.setText(
            self.tr("🎚 No recommendation yet — pick a strategy and click Recommend Playlist.")
            if no_recommendation
            else ""
        )
        self.empty_state_label.setVisible(no_recommendation)
        self.variant_label.setText(vm.applied_variant_label(state))
        self.proceed_button.setEnabled(vm.can_proceed(state))
        rows = vm.copilot_variants_for_display(state)
        if lightweight:
            self.copilot_table.setHidden(len(rows) == 0)
            self.apply_variant_button.setHidden(len(rows) == 0)
        else:
            self._populate_copilot_table(rows)
        self.applied_copilot_variant_label.setHidden(state.applied_variant_name is None)

        anchor = vm.anchor_summary(state)
        text = (
            self.tr("Anchor: {0}").format(anchor)
            if anchor
            else self.tr("Select a track in the Library to set the anchor.")
        )
        self.anchor_label.setText(text)
        self.anchor_label.setVisible(bool(state.scanned_records))

        self._refresh_strategy_explanation(vm)

        self.recommendation_vs_copilot_label.setText(vm.recommendation_vs_copilot_text())
        self.constraint_explanation_label.setText(vm.constraint_explanation())

        rec_summary = vm.recommendation_summary(state)
        self.recommendation_summary_label.setText(rec_summary or "")
        self.recommendation_summary_label.setVisible(rec_summary is not None)

        excluded = len(state.excluded_paths)
        locked = len(state.locked_paths)
        parts = []
        if excluded:
            parts.append(self.tr("{0} excluded").format(excluded))
        if locked:
            parts.append(self.tr("{0} locked").format(locked))
        self.constraints_label.setText(", ".join(parts) if parts else "")
        self.clear_constraints_button.setEnabled(bool(excluded or locked))

    def _refresh_strategy_explanation(self, vm: BuildViewModel) -> None:
        current_strategy = self.strategy_combo.currentData() or self.strategy_combo.currentText()
        self.strategy_explanation_label.setText(vm.strategy_explanation(current_strategy))

    def _render_recommend_progress(self, state: AppState) -> None:
        if not state.is_recommending:
            self.recommend_progress_bar.setVisible(False)
            self.recommend_progress_label.setVisible(False)
            self.recommend_progress_label.setText("")
            return
        self.recommend_progress_bar.setValue(
            progress_percent(state.recommend_progress_count, state.recommend_progress_total)
        )
        self.recommend_progress_label.setText(
            progress_status_text(
                state.recommend_progress_count,
                state.recommend_progress_total,
                state.recommend_elapsed_seconds,
            )
        )
        self.recommend_progress_bar.setVisible(True)
        self.recommend_progress_label.setVisible(True)

    def _populate_copilot_table(self, rows: list[CopilotVariantRow]) -> None:
        self.copilot_table.setRowCount(0)
        for row_data in rows:
            row = self.copilot_table.rowCount()
            self.copilot_table.insertRow(row)
            status = row_data.readiness_status
            readiness_label = self.tr(_READINESS_STATUS_LABELS.get(status, status))
            values = [
                row_data.name,
                row_data.description,
                str(row_data.track_count),
                readiness_label,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 3:
                    color = _READINESS_STATUS_COLORS.get(status)
                    if color:
                        item.setBackground(QColor(color))
                        item.setForeground(QColor("#061016"))
                    item.setToolTip(row_data.readiness_summary)
                self.copilot_table.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_recommend(self) -> None:
        strategy = self.strategy_combo.currentData()
        self.recommend_requested.emit(strategy, [])

    def _on_strategy_changed(self, _index: int) -> None:
        if self._last_vm is not None:
            self._refresh_strategy_explanation(self._last_vm)

    def _on_apply_variant(self) -> None:
        selected_rows = self.copilot_table.selectedItems()
        if not selected_rows:
            return
        row = self.copilot_table.currentRow()
        self.copilot_variant_applied.emit(row)
