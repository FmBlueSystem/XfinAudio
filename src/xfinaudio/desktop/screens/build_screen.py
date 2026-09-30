"""BuildScreen — thin QWidget that renders BuildViewModel data."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
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


def _copilot_rows_signature(rows: list[CopilotVariantRow]) -> tuple:
    """Return a comparable signature of the copilot rows shown in the table.

    render() is called on every state sync for the visible Build tab, so the
    signature lets the screen skip the destructive table rebuild when the rows
    are unchanged and keep the DJ's selection alive.
    """
    return (
        len(rows),
        tuple(
            (
                row.name,
                row.description,
                row.track_count,
                row.readiness_status,
                row.readiness_summary,
                row.blocker_count,
                row.warning_count,
                row.pool_notes,
            )
            for row in rows
        ),
    )


_COPILOT_COLUMNS = ["Variant", "Description", "Tracks", "Readiness"]
_COPILOT_HEADER_TOOLTIPS = [
    "Name of this Prep Copilot playlist variant",
    "How this variant was assembled and what it emphasizes",
    "Number of tracks in this variant",
    "DJ readiness: Ready, Needs Review, or Blocked",
]


ANY_GENRE = "Any genre"


class BuildScreen(QWidget):
    """Displays strategy selection and Prep Copilot controls."""

    recommend_requested = Signal(str, list)
    spectral_cohesion_changed = Signal(int)
    copilot_generate_requested = Signal()
    copilot_ask_requested = Signal(str)
    copilot_variant_applied = Signal(int)
    apply_without_selection_requested = Signal()
    # Emitted when an anchor suggestion moves the genre combo off "Any genre":
    # the DJ's next search is silently narrowed to one genre, so the change is
    # reported to the status label instead of staying invisible (E2E finding:
    # pool 63 -> 4 with no explanation).
    genre_suggested_from_anchor = Signal(str)
    back_requested = Signal()
    exclude_requested = Signal()
    lock_requested = Signal()
    clear_constraints_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._last_vm: BuildViewModel | None = None
        # Signature of the copilot rows currently in the table. render() runs on
        # every state sync for the visible tab, and rebuilding the table would
        # wipe the DJ's selection even when the rows are identical.
        self._last_copilot_signature: tuple | None = None
        self._variant_rows: list[CopilotVariantRow] = []
        self._variant_target_count = 25
        self._needs_metadata_repair = False
        self._genre_chosen_by_dj = False
        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(8)
        controls = QWidget()
        layout = QVBoxLayout(controls)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.controls_scroll = QScrollArea()
        self.controls_scroll.setWidgetResizable(True)
        self.controls_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.controls_scroll.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.controls_scroll.setMinimumHeight(120)
        self.controls_scroll.setWidget(controls)
        outer.addWidget(self.controls_scroll)

        # Strategy row
        strategy_row = QHBoxLayout()
        self.strategy_combo = QComboBox()
        # Genre sits beside the strategy because they are separate choices: the
        # shape of a set and the corner of the library it is drawn from. Coupling
        # them meant a genre-locked set had to give up its energy arc.
        self.genre_combo = QComboBox()
        self.genre_combo.addItem(ANY_GENRE)
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
        strategy_row.addWidget(self.genre_combo)
        strategy_row.addWidget(self.recommend_button)
        strategy_row.addWidget(self.recommend_progress_bar)
        strategy_row.addWidget(self.recommend_progress_label)
        strategy_row.addStretch()
        layout.addLayout(strategy_row)

        # Guidance labels — keep compact so the table gets vertical space.
        self.anchor_label = QLabel()
        self.anchor_label.setWordWrap(True)
        self.anchor_label.setMaximumHeight(40)
        anchor_row = QHBoxLayout()
        anchor_row.addWidget(self.anchor_label, 1)
        self.anchor_action_button = QPushButton(self.tr("Choose a starting track"))
        self.anchor_action_button.setToolTip(self.tr("Select a complete track in Library, or repair missing metadata"))
        self.anchor_action_button.setAccessibleName(self.tr("Choose starting track or repair metadata"))
        self.anchor_action_button.hide()
        anchor_row.addWidget(self.anchor_action_button)
        layout.addLayout(anchor_row)

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
        # Give the natural-language prompt its own row so compact windows keep
        # enough typing space instead of collapsing it between action buttons.
        self.copilot_ask_input = QLineEdit()
        self.copilot_ask_input.setObjectName("copilot_ask_input")
        self.copilot_ask_input.setPlaceholderText(
            self.tr("Describe the set you want (for example: 45 minutes of deep house)")
        )
        self.copilot_ask_button = QPushButton(self.tr("Ask Copilot"))
        self.copilot_ask_button.setObjectName("copilot_ask_button")
        self.copilot_ask_button.setEnabled(False)
        self.variant_label = QLabel()
        copilot_row.addWidget(QLabel(self.tr("Set Tracks")))
        copilot_row.addWidget(self.target_count_input)
        copilot_row.addWidget(self.genre_focus_input)
        copilot_row.addWidget(self.copilot_button)
        copilot_row.addWidget(self.variant_label)
        copilot_row.addStretch()
        layout.addLayout(copilot_row)
        ask_row = QHBoxLayout()
        ask_row.addWidget(self.copilot_ask_input, 1)
        ask_row.addWidget(self.copilot_ask_button)
        layout.addLayout(ask_row)

        # AI copilot status line: its own row, because the controls row above cannot
        # give a wrapping message the width it needs without squeezing the input.
        self.copilot_ask_status = QLabel("")
        self.copilot_ask_status.setObjectName("copilot_ask_status")
        self.copilot_ask_status.setWordWrap(True)
        self.copilot_ask_status.setMaximumHeight(36)
        layout.addWidget(self.copilot_ask_status)

        # Scroll only the controls on short displays; variants and Apply remain
        # outside the scroll area and reachable without hunting for the action.
        layout = outer
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
        copilot_header = self.copilot_table.horizontalHeader()
        # Free width goes to Description, which holds a sentence; the others
        # hold a name, a count and a status word.
        copilot_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for name in ("Variant", "Tracks", "Readiness"):
            copilot_header.setSectionResizeMode(_COPILOT_COLUMNS.index(name), QHeaderView.ResizeMode.ResizeToContents)
        self.copilot_table.setAlternatingRowColors(True)
        self.copilot_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.copilot_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.copilot_table.setMinimumHeight(130)
        self.copilot_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.copilot_table, 1)

        self.variant_details_label = QLabel()
        self.variant_details_label.setWordWrap(True)
        self.variant_details_label.setAccessibleName(self.tr("Selected variant details"))
        self.variant_details_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.variant_details_label.hide()
        layout.addWidget(self.variant_details_label)

        # Applied variant badge (set imperatively by main_window)
        self.applied_copilot_variant_label = QLabel(self.tr("Applied Variant: none"))
        self.applied_copilot_variant_label.setToolTip(self.tr("No Prep Copilot variant is currently applied."))
        layout.addWidget(self.applied_copilot_variant_label)

        # Apply variant button
        self.apply_variant_button = QPushButton(self.tr("Apply Selected Variant"))
        layout.addWidget(self.apply_variant_button)

        # No spacer here: the copilot table above carries the stretch and pushes
        # the nav row down on its own. A trailing addStretch would compete with
        # it for the free height, leaving the table about three rows tall.

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
            self.copilot_ask_button: "Ask the AI copilot to turn your request into Prep Copilot variants",
            self.apply_variant_button: "Apply the selected Prep Copilot variant",
            self.back_button: "Return to the Library screen",
            self.proceed_button: "Move on to review the recommended playlist",
        }
        for button, tip in tips.items():
            button.setToolTip(self.tr(tip))

    def _setup_accessibility(self) -> None:
        """Set accessible names for screen readers."""
        self.strategy_combo.setAccessibleName(self.tr("Recommendation strategy"))
        self.genre_combo.setAccessibleName(self.tr("Genre for this set"))
        self.recommend_button.setAccessibleName(self.tr("Recommend playlist"))
        self.spectral_cohesion_slider.setAccessibleName(self.tr("Spectral cohesion"))
        self.exclude_button.setAccessibleName(self.tr("Exclude selected tracks"))
        self.lock_button.setAccessibleName(self.tr("Lock selected tracks"))
        self.clear_constraints_button.setAccessibleName(self.tr("Clear constraints"))
        self.target_count_input.setAccessibleName(self.tr("Target track count"))
        self.genre_focus_input.setAccessibleName(self.tr("Genre focus"))
        self.copilot_button.setAccessibleName(self.tr("Generate Prep Copilot variants"))
        self.copilot_ask_input.setAccessibleName(self.tr("Set request for the AI copilot"))
        self.copilot_ask_button.setAccessibleName(self.tr("Ask the AI copilot"))
        self.copilot_ask_status.setAccessibleName(self.tr("AI copilot status"))
        self.copilot_table.setAccessibleName(self.tr("Prep Copilot variants"))
        self.apply_variant_button.setAccessibleName(self.tr("Apply selected Prep Copilot variant"))
        self.back_button.setAccessibleName(self.tr("Back to library"))
        self.proceed_button.setAccessibleName(self.tr("Proceed to review"))

    def _setup_tab_order(self) -> None:
        """Define a logical keyboard tab order across primary controls."""
        self.setTabOrder(self.strategy_combo, self.genre_combo)
        self.setTabOrder(self.genre_combo, self.recommend_button)
        self.setTabOrder(self.recommend_button, self.anchor_action_button)
        self.setTabOrder(self.anchor_action_button, self.spectral_cohesion_slider)
        self.setTabOrder(self.spectral_cohesion_slider, self.exclude_button)
        self.setTabOrder(self.exclude_button, self.lock_button)
        self.setTabOrder(self.lock_button, self.clear_constraints_button)
        self.setTabOrder(self.clear_constraints_button, self.target_count_input)
        self.setTabOrder(self.target_count_input, self.genre_focus_input)
        self.setTabOrder(self.genre_focus_input, self.copilot_button)
        self.setTabOrder(self.copilot_button, self.copilot_ask_input)
        self.setTabOrder(self.copilot_ask_input, self.copilot_ask_button)
        self.setTabOrder(self.copilot_ask_button, self.copilot_table)
        self.setTabOrder(self.copilot_table, self.apply_variant_button)
        self.setTabOrder(self.apply_variant_button, self.back_button)
        self.setTabOrder(self.back_button, self.proceed_button)

    def _connect_signals(self) -> None:
        self.back_button.clicked.connect(self.back_requested)
        self.copilot_button.clicked.connect(self.copilot_generate_requested)
        self.copilot_ask_button.clicked.connect(self._on_copilot_ask)
        self.copilot_ask_input.returnPressed.connect(self._on_copilot_ask)
        self.apply_variant_button.clicked.connect(self._on_apply_variant)
        self.copilot_table.itemSelectionChanged.connect(self._refresh_variant_details)
        self.recommend_button.clicked.connect(self._on_recommend)
        self.exclude_button.clicked.connect(self.exclude_requested)
        self.lock_button.clicked.connect(self.lock_requested)
        self.clear_constraints_button.clicked.connect(self.clear_constraints_requested)
        self.spectral_cohesion_slider.valueChanged.connect(self._on_spectral_cohesion_changed)
        self.strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)
        self.genre_combo.activated.connect(self._on_genre_activated)

    def connect_signals(self, window: Any) -> None:
        self.copilot_table.itemDoubleClicked.connect(window._apply_prep_copilot_item)
        self.recommend_requested.connect(window._on_recommend_requested)
        self.spectral_cohesion_changed.connect(window._settings_controller.on_spectral_cohesion_changed)
        self.copilot_generate_requested.connect(window.generate_prep_copilot)
        self.copilot_ask_requested.connect(window.ask_ai_copilot)
        self.copilot_variant_applied.connect(window._on_copilot_variant_applied)
        self.apply_without_selection_requested.connect(
            lambda: window.status_label.setText(self.tr("Generate and select a Prep Copilot variant before applying"))
        )
        self.genre_suggested_from_anchor.connect(
            lambda genre: window.status_label.setText(
                self.tr("Genre set to {0} from the anchor — switch back to Any genre to use the whole library").format(
                    genre
                )
            )
        )
        self.back_requested.connect(lambda: window.workflow_tabs.setCurrentIndex(0))
        self.anchor_action_button.clicked.connect(lambda: self._choose_anchor(window))
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

        self.recommend_button.setEnabled(vm.recommend_button_enabled(state))
        self.copilot_button.setEnabled(vm.copilot_button_enabled(state))
        # Render-driven on purpose: the coalesced 200ms render walks every screen, so
        # an enabled state set imperatively here would come back on the next sync.
        self.copilot_ask_button.setEnabled(vm.copilot_ask_button_enabled(state))
        if vm.is_asking_copilot(state):
            # Only the busy text is render-owned. The success/failure message is
            # written by the controller and must survive the next idle render.
            self.copilot_ask_status.setText(self.tr("Asking the AI copilot... this can take up to a minute"))
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
        if rows and no_recommendation:
            self.empty_state_label.setText(self.tr("Select a variant, then click Use to review this set."))
        self._variant_rows = rows
        if state.last_prep_copilot_plan is not None:
            self._variant_target_count = state.last_prep_copilot_plan.intent.target_track_count
        self.copilot_table.setVisible(bool(rows))
        self.apply_variant_button.setVisible(bool(rows))
        if not lightweight:
            signature = _copilot_rows_signature(rows)
            if signature != self._last_copilot_signature:
                self._populate_copilot_table(rows)
                self._last_copilot_signature = signature
        self._refresh_variant_details()
        self.applied_copilot_variant_label.setHidden(state.applied_variant_name is None)

        anchor = vm.anchor_summary(state)
        text = (
            self.tr("Anchor: {0}").format(anchor)
            if anchor
            else self.tr("Select a track in the Library to set the anchor.")
        )
        self.anchor_label.setText(text)
        self.anchor_label.setVisible(bool(state.scanned_records))
        self._needs_metadata_repair = not any(r.metadata_status == "complete" for r in state.scanned_records)
        self.anchor_action_button.setText(
            self.tr("Fix missing metadata") if self._needs_metadata_repair else self.tr("Choose a starting track")
        )
        self.anchor_action_button.setVisible(bool(state.scanned_records) and not vm.has_complete_anchor(state))
        self.anchor_action_button.setEnabled(vm.generation_idle(state))
        if self._needs_metadata_repair and state.scanned_records:
            self.anchor_label.setText(
                self.tr("No complete tracks. Fix missing metadata, then refresh the library scan.")
            )

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

    def invalidate_copilot_cache(self) -> None:
        """Drop the cached copilot row signature so the next render repopulates.

        External code clears `copilot_table` directly (e.g. the Prep Copilot
        controller's no-tracks branch bypasses `_populate_copilot_table`), so the
        signature would otherwise still describe the cleared rows and a later render
        of identical variants would skip rebuilding, leaving the table empty.
        """
        self._last_copilot_signature = None

    def _populate_copilot_table(self, rows: list[CopilotVariantRow]) -> None:
        """Rebuild the variants table, restoring same-index selection when possible.

        setRowCount(0) destroys selection and currentRow, so the previous current
        row is remembered and re-selected when the new row count matches. When the
        count changed, the selection would point at different data, so it resets.
        """
        previous_row = self.copilot_table.currentRow()
        previous_count = self.copilot_table.rowCount()
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
                if col == 2 and row_data.pool_notes:
                    # Tracks cell carries the pool diagnostics: a DJ hovering a
                    # 1-track variant sees exactly which filter step shrank it.
                    item.setToolTip(row_data.pool_notes)
                if col == 3:
                    color = _READINESS_STATUS_COLORS.get(status)
                    if color:
                        item.setBackground(QColor(color))
                        item.setForeground(QColor("#061016"))
                    tooltip = row_data.readiness_summary
                    if row_data.pool_notes:
                        tooltip = f"{tooltip}\n\n{row_data.pool_notes}"
                    item.setToolTip(tooltip)
                self.copilot_table.setItem(row, col, item)
        if len(rows) == previous_count and 0 <= previous_row < len(rows):
            self.copilot_table.selectRow(previous_row)
        elif rows:
            self.copilot_table.selectRow(next((i for i, row in enumerate(rows) if row.name == "balanced"), 0))

    def _refresh_variant_details(self) -> None:
        index = self.copilot_table.currentRow()
        selected = bool(self.copilot_table.selectedIndexes()) and 0 <= index < len(self._variant_rows)
        self.variant_details_label.setVisible(selected)
        self.apply_variant_button.setEnabled(selected)
        if not selected:
            self.variant_details_label.clear()
            self.apply_variant_button.setText(self.tr("Apply Selected Variant"))
            return
        row = self._variant_rows[index]
        self.apply_variant_button.setText(self.tr("Use {0} · {1} tracks").format(row.name, row.track_count))
        summary = self.tr("{0} of {1} requested · {2}").format(
            row.track_count, self._variant_target_count, row.readiness_summary
        )
        self.variant_details_label.setText("\n".join(part for part in (summary, row.pool_notes) if part))

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _choose_anchor(self, window: Any) -> None:
        if self._needs_metadata_repair:
            window.workflow_tabs.setCurrentIndex(5)
            return
        library = window._library_screen
        library.clear_quick_filters(emit_signal=False)
        library.search_input.clear()
        library.complete_filter_button.click()
        window.workflow_tabs.setCurrentIndex(0)

    def _on_recommend(self) -> None:
        strategy = self.strategy_combo.currentData()
        self.recommend_requested.emit(strategy, [])

    def _on_copilot_ask(self) -> None:
        """Emit the typed request from both entry points (button and Return)."""
        if self.copilot_ask_button.isEnabled():
            self.copilot_ask_requested.emit(self.copilot_ask_input.text())

    def _on_strategy_changed(self, _index: int) -> None:
        if self._last_vm is not None:
            self._refresh_strategy_explanation(self._last_vm)

    def _on_apply_variant(self) -> None:
        selected_rows = self.copilot_table.selectedItems()
        if not selected_rows:
            # Surface guidance instead of failing silently: the button looks
            # dead otherwise when no variant was generated or selected yet.
            self.apply_without_selection_requested.emit()
            return
        row = self.copilot_table.currentRow()
        self.copilot_variant_applied.emit(row)

    # ------------------------------------------------------------------
    # Genre selection
    # ------------------------------------------------------------------

    def _on_genre_activated(self, _index: int) -> None:
        self._genre_chosen_by_dj = True

    def suggest_genre_from_anchor(self, genre: str | None) -> None:
        """Follow an anchor's offered genre until the DJ makes an explicit choice.

        When the suggestion moves the selection off "Any genre", the whole-library
        search the DJ believes they are running becomes a single-genre search, so
        the change is reported through `genre_suggested_from_anchor`. A DJ-made
        choice is never touched, and a suggestion that changes nothing stays silent.
        """
        if self._genre_chosen_by_dj or genre is None:
            return
        index = self.genre_combo.findText(genre.strip())
        if index < 0:
            return
        was_any_genre = self.selected_genre() is None
        self.genre_combo.setCurrentIndex(index)
        if was_any_genre and self.selected_genre() is not None:
            self.genre_suggested_from_anchor.emit(genre.strip())

    def set_available_genres(self, genres: list[str]) -> None:
        """Offer *genres*, keeping whatever the DJ already picked if it survives.

        Re-scanning the library must not silently reset the set being built, so
        the current choice is restored when it is still on offer and falls back
        to every genre when it is not.
        """
        previous = self.selected_genre()
        listed = sorted({genre.strip() for genre in genres if genre and genre.strip()})
        self.genre_combo.blockSignals(True)
        self.genre_combo.clear()
        self.genre_combo.addItem(ANY_GENRE)
        for genre in listed:
            self.genre_combo.addItem(genre)
        if previous is not None:
            index = self.genre_combo.findText(previous)
            self.genre_combo.setCurrentIndex(max(index, 0))
        self.genre_combo.blockSignals(False)

    def selected_genre(self) -> str | None:
        """Return the chosen genre, or None when the whole library is in play."""
        current = self.genre_combo.currentText()
        return None if current == ANY_GENRE or not current else current
