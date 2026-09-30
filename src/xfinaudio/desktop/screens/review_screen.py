"""ReviewScreen — thin QWidget that renders ReviewViewModel data."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.review_assistance import preview_engine_replacement, review_engine_facts
from xfinaudio.desktop.review_view_model import (
    ReadinessCheckRow,
    RecommendationRow,
    ReviewViewModel,
)

_READINESS_COLUMNS = ["Check", "Status", "Detail"]
_RECOMMENDATION_COLUMNS = ["#", "Title", "Artist", "BPM", "Key", "Energy", "Color"]
# Score headers are deliberately short: each cell holds five characters, and
# longer titles ("Energy Score") sized their columns off the header instead,
# starving the stretched Warnings column. The tooltips carry the full meaning.
_TRANSITION_COLUMNS = [
    "Order",
    "From",
    "To",
    "Key",
    "BPM",
    "Energy",
    "Fit",
    "Blend",
    "Tag",
    "Final",
    "Warnings",
]

# Header tooltips for the transition review table
_TRANSITION_HEADER_TOOLTIPS = {
    0: "Position of this transition in the playlist",
    1: "First track in the transition",
    2: "Second track in the transition",
    3: (
        "Tonal compatibility (Camelot). 1.0 = same key, 0.9 = adjacent or diagonal, "
        "0.85 = relative A/B, 0.0 = incompatible"
    ),
    4: "BPM similarity. 1.0 = ≤2% difference, drops as the gap grows",
    5: "Energy level similarity. 1.0 = same energy, drops as levels diverge",
    6: "Do these tracks belong in the same set? Harmony, tags, danceability and spectral colour.",
    7: "Can these tracks be joined? Tempo and the energy handoff from the outgoing to the incoming section.",
    8: "Genre/tag overlap. Higher = more shared tags or genres",
    9: "Weighted average of all components. Component weights depend on the selected strategy",
    10: "Alerts about potential issues in this transition",
}

_READINESS_HEADER_TOOLTIPS = {
    0: "Category being validated",
    1: "Ready, Needs Review, or Blocked",
    2: "Specific explanation for this check",
}

_RECOMMENDATION_HEADER_TOOLTIPS = {
    0: "Track position in the recommended playlist",
    1: "Track title",
    2: "Artist or performer name",
    3: "Beats per minute — tempo of the track",
    4: "Musical key in Camelot notation",
    5: "Energy level from 1 (calm) to 10 (intense)",
    6: "Spectral color profile (RED/GREEN/BLUE)",
}

# Color coding for score cells
_SCORE_COLOR_EXCELLENT = QColor("#1a3a2a")
_SCORE_COLOR_GOOD = QColor("#3a3010")
_SCORE_COLOR_POOR = QColor("#4a1a1a")
_SCORE_TEXT_EXCELLENT = QColor("#1fd16a")
_SCORE_TEXT_GOOD = QColor("#ffb000")
_SCORE_TEXT_POOR = QColor("#ff4d4f")


def _recommendation_rows_signature(rows: list[RecommendationRow]) -> tuple:
    """Return a comparable signature of the recommendation rows shown in the table.

    render() runs on every coalesced state sync while the Review tab is visible
    (~5 times per second during scans), and rebuilding the table would wipe the
    DJ's selection even when the rows are identical. The signature covers every
    rendered cell value plus the UserRole path stored behind column 0.
    """
    return (
        len(rows),
        tuple(
            (
                row.position,
                row.title,
                row.artist,
                row.bpm,
                row.camelot_key,
                row.energy,
                row.spectral_color,
                row.overall_score,
                row.path,
            )
            for row in rows
        ),
    )


class _ReviewContent(QWidget):
    def heightForWidth(self, width: int) -> int:
        # QScrollArea otherwise treats preferred table heights as mandatory
        # when wrapping labels participate in height-for-width calculation.
        layout = self.layout()
        return layout.minimumHeightForWidth(width) if isinstance(layout, QVBoxLayout) else -1


class _NarratorStatusLabel(QLabel):
    def setText(self, text: str) -> None:
        super().setText(text)
        # Empty QLabel still reserves a text row; return that space to tables.
        self.setVisible(bool(text))


class ReviewScreen(QWidget):
    """Displays readiness status, track list, and transition analysis."""

    back_requested = Signal()
    proceed_to_export_requested = Signal()
    save_to_playlists_requested = Signal()
    ai_narrate_requested = Signal()  # "Explícame este set": ask the AI to narrate the set
    configure_ai_requested = Signal()
    ai_narrate_cancel_requested = Signal()
    track_remove_requested = Signal(str)  # emits the track path
    track_play_requested = Signal(str)  # emits the track path
    remove_without_selection_requested = Signal()  # no valid row selected for removal
    play_without_path_requested = Signal()  # double-clicked row has no playable path

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Signature of the recommendation rows currently in the table. render()
        # runs on every state sync for the visible tab, and rebuilding the table
        # would wipe the DJ's selection even when the rows are identical.
        self._last_recommendation_signature: tuple | None = None
        self._selected_transition_context: tuple[str, ...] | None = None
        self._rendered_state = AppState()
        self._replacement_context: tuple | None = None
        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(6)
        content = _ReviewContent()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll.setWidget(content)
        outer.addWidget(self.content_scroll, 1)

        # 1. Decision banner — primary semaphore, large and prominent
        self.readiness_badge = QLabel()
        self.readiness_badge.setObjectName("readinessBadge")
        layout.addWidget(self.readiness_badge)

        # 2. Reason summary — keep compact so tables get space
        self.dj_readiness_label = QLabel(self.tr("DJ Readiness: No recommendation ready."))
        self.dj_readiness_label.setMaximumHeight(28)
        layout.addWidget(self.dj_readiness_label)

        # Quality summary (set imperatively by main_window). This is the only
        # place the transition score is reported; a second VM-driven label used
        # to restate a subset of it on the next line.
        self.review_summary_label = QLabel(self.tr("No recommendation is ready for review."))
        self.review_summary_label.setMaximumHeight(28)
        layout.addWidget(self.review_summary_label)

        # 3. Recommendation table
        self.recommendation_table = QTableWidget(0, len(_RECOMMENDATION_COLUMNS))
        self.recommendation_table.setHorizontalHeaderLabels([self.tr(c) for c in _RECOMMENDATION_COLUMNS])
        header = self.recommendation_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col in (0, 3, 4, 5):  # #, BPM, Key, Energy — content-sized
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.recommendation_table.setAlternatingRowColors(True)
        self.recommendation_table.verticalHeader().setVisible(False)
        self.recommendation_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._apply_header_tooltips(self.recommendation_table, _RECOMMENDATION_HEADER_TOOLTIPS)
        layout.addWidget(self.recommendation_table, 1)

        # Action row for the recommendation table
        actions = QHBoxLayout()
        self.remove_track_button = QPushButton(self.tr("Remove from Playlist"))
        self.remove_track_button.setEnabled(False)
        actions.addWidget(self.remove_track_button)
        self.save_to_playlists_button = QPushButton(self.tr("Save to My Playlists"))
        self.save_to_playlists_button.setEnabled(False)
        actions.addWidget(self.save_to_playlists_button)
        # Set-level AI narrative. It complements the deterministic per-track
        # explainability already carried by the row tooltips: this button asks the
        # LLM to narrate the whole arc, and the label below it shows the answer.
        self.ai_narrate_button = QPushButton(self.tr("Explícame este set"))
        self.ai_narrate_button.setObjectName("ai_narrate_button")
        self.ai_narrate_button.setEnabled(False)
        actions.addWidget(self.ai_narrate_button)
        self.ai_narrate_cancel_button = QPushButton(self.tr("Cancel"))
        self.ai_narrate_cancel_button.setVisible(False)
        actions.addWidget(self.ai_narrate_cancel_button)
        self.configure_ai_button = QPushButton(self.tr("Configure AI"))
        actions.addWidget(self.configure_ai_button)
        actions.addStretch()
        layout.addLayout(actions)
        # Local evidence gets its own row; optional AI controls must not widen
        # the entire workflow stack when Review is not even the visible screen.
        actions = QHBoxLayout()
        self.engine_facts_button = QPushButton(self.tr("Engine facts & alternatives"))
        self.engine_facts_button.setCheckable(True)
        self.engine_facts_button.setEnabled(False)
        actions.addWidget(self.engine_facts_button)
        self.compare_replacement_button = QPushButton(self.tr("Compare replacement"))
        self.compare_replacement_button.setEnabled(False)
        actions.addWidget(self.compare_replacement_button)
        actions.addStretch()
        layout.addLayout(actions)

        self.engine_facts_details = QPlainTextEdit()
        self.engine_facts_details.setReadOnly(True)
        self.engine_facts_details.setMaximumHeight(110)
        self.engine_facts_details.setVisible(False)
        self.engine_facts_details.setAccessibleName(self.tr("Local engine facts and alternative comparison"))
        layout.addWidget(self.engine_facts_details)

        self.replacement_details = QPlainTextEdit()
        self.replacement_details.setReadOnly(True)
        self.replacement_details.setMaximumHeight(100)
        self.replacement_details.setVisible(False)
        self.replacement_details.setAccessibleName(self.tr("Engine replacement comparison preview"))
        layout.addWidget(self.replacement_details)

        # The narrative is read-only text from state, so a wrapping label is
        # enough -- a text edit would claim focus and look like an input the DJ
        # never types into. The label is adaptive: measured, a 150-word narrative
        # takes ~75px at 1200px wide and ~138px at 550px wide, and it is capped at
        # 150px so it can never eat the whole screen. It stays hidden while empty,
        # so an idle Review screen loses no height to it.
        self.ai_narrative_label = QLabel()
        self.ai_narrative_label.setObjectName("ai_narrative_label")
        self.ai_narrative_label.setWordWrap(True)
        self.ai_narrative_label.setTextFormat(Qt.TextFormat.PlainText)
        self.ai_narrative_label.setToolTip(self.tr("AI-generated commentary; verify against local engine facts"))
        self.ai_narrative_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.ai_narrative_label.setMaximumHeight(150)
        self.ai_narrative_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.ai_narrative_label.setVisible(False)
        layout.addWidget(self.ai_narrative_label)

        # Narrator status line: its own row, because the controls row above cannot
        # give a wrapping message the width it needs.
        self.ai_narrate_status = _NarratorStatusLabel()
        self.ai_narrate_status.setText("")
        self.ai_narrate_status.setObjectName("ai_narrate_status")
        self.ai_narrate_status.setWordWrap(True)
        self.ai_narrate_status.setTextFormat(Qt.TextFormat.PlainText)
        self.ai_narrate_status.setMaximumHeight(36)
        layout.addWidget(self.ai_narrate_status)

        # 4. Transition table help label
        self.transition_help_label = QLabel(
            self.tr(
                "💡 Each row shows how two consecutive tracks blend. "
                "Green = excellent, Yellow = acceptable, Red = risky. "
                "Select a score with the arrow keys or mouse for details below. Tab moves to the details."
            )
        )
        self.transition_help_label.setWordWrap(True)
        self.transition_help_label.setMaximumHeight(40)
        self.transition_help_label.setStyleSheet("color: #93aac4; font-size: 12px; padding: 4px 0;")
        layout.addWidget(self.transition_help_label)

        # 5. Transition table
        self.transition_table = QTableWidget(0, len(_TRANSITION_COLUMNS))
        self.transition_table.setHorizontalHeaderLabels([self.tr(c) for c in _TRANSITION_COLUMNS])
        transition_header = self.transition_table.horizontalHeader()
        # Free width goes to From/To/Warnings; the rest hold an index or a
        # five-character score and only need what they show. Final widths come
        # from theme._REVIEW_TABLE_COLUMN_WIDTHS, applied later by
        # apply_compact_table_columns.
        transition_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for name in ("Order", "Key", "BPM", "Energy", "Tag", "Fit", "Blend", "Final"):
            transition_header.setSectionResizeMode(
                _TRANSITION_COLUMNS.index(name), QHeaderView.ResizeMode.ResizeToContents
            )
        self.transition_table.setTabKeyNavigation(False)
        self.transition_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.transition_table.setAlternatingRowColors(True)
        self.transition_table.verticalHeader().setVisible(False)
        self.transition_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._apply_header_tooltips(self.transition_table, _TRANSITION_HEADER_TOOLTIPS)
        layout.addWidget(self.transition_table, 1)

        # Reuse the deterministic table explanations; keyboard users can select,
        # copy and scroll long details without relying on hover or an AI request.
        self.transition_details = QPlainTextEdit()
        self.transition_details.setObjectName("transition_details")
        self.transition_details.setReadOnly(True)
        self.transition_details.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.transition_details.setTabChangesFocus(True)
        self.transition_details.setMinimumHeight(64)
        self.transition_details.setMaximumHeight(96)
        self.transition_details.setVisible(False)
        layout.addWidget(self.transition_details)

        # 6. Readiness checks table (secondary)
        self.readiness_table = QTableWidget(0, len(_READINESS_COLUMNS))
        self.readiness_table.setHorizontalHeaderLabels([self.tr(c) for c in _READINESS_COLUMNS])
        readiness_header = self.readiness_table.horizontalHeader()
        # Check and Status are short labels; Detail carries the sentence.
        readiness_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for name in ("Check", "Status"):
            readiness_header.setSectionResizeMode(
                _READINESS_COLUMNS.index(name), QHeaderView.ResizeMode.ResizeToContents
            )
        self.readiness_table.setAlternatingRowColors(True)
        self.readiness_table.verticalHeader().setVisible(False)
        self.readiness_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._apply_header_tooltips(self.readiness_table, _READINESS_HEADER_TOOLTIPS)
        layout.addWidget(self.readiness_table, 1)

        # No spacer here: the three tables above already carry stretch 1 and an
        # Expanding size policy, so they push the nav row down on their own. A
        # trailing addStretch would compete with them for the free height and
        # take a quarter of it, leaving each table about two rows tall.

        # Navigation
        nav = QHBoxLayout()
        self.back_button = QPushButton(self.tr("← Build"))
        self.export_button = QPushButton(self.tr("Export →"))
        self.export_button.setObjectName("primaryAction")
        nav.addWidget(self.back_button)
        nav.addStretch()
        nav.addWidget(self.export_button)
        outer.addLayout(nav)

        self._setup_button_tooltips()
        self._setup_accessibility()
        self._setup_tab_order()

    def _setup_button_tooltips(self) -> None:
        """Explain every button so users understand each control (R1)."""
        tips = {
            self.remove_track_button: "Remove the selected track from the playlist",
            self.save_to_playlists_button: "Save this recommendation to My Playlists",
            self.ai_narrate_button: (
                "Ask the AI to explain this set: how it opens, how it moves, and where it lands, "
                "using only the facts the engine produced"
            ),
            self.ai_narrate_cancel_button: "Cancel this narrative request; local analysis remains available",
            self.configure_ai_button: "Open AI settings to enable or configure the optional narrator",
            self.engine_facts_button: "Explain risks and compare existing engine variants without a network call",
            self.compare_replacement_button: "Preview an engine replacement for the selected track without applying it",
            self.back_button: "Return to the Build screen",
            self.export_button: "Move on to export this playlist",
        }
        for button, tip in tips.items():
            button.setToolTip(self.tr(tip))

    def _setup_accessibility(self) -> None:
        """Set accessible names for screen readers."""
        self.readiness_badge.setAccessibleName(self.tr("DJ readiness badge"))
        self.dj_readiness_label.setAccessibleName(self.tr("DJ readiness summary"))
        self.recommendation_table.setAccessibleName(self.tr("Recommended playlist"))
        self.remove_track_button.setAccessibleName(self.tr("Remove selected track from playlist"))
        self.save_to_playlists_button.setAccessibleName(self.tr("Save recommendation to My Playlists"))
        self.ai_narrate_button.setAccessibleName(self.tr("Explain this set with the AI narrator"))
        self.ai_narrate_cancel_button.setAccessibleName(self.tr("Cancel AI narration"))
        self.configure_ai_button.setAccessibleName(self.tr("Configure AI"))
        self.engine_facts_button.setAccessibleName(self.tr("Show local engine facts and alternatives"))
        self.compare_replacement_button.setAccessibleName(
            self.tr("Compare an engine replacement for the selected track")
        )
        self.ai_narrative_label.setAccessibleName(self.tr("AI set narrative"))
        self.ai_narrate_status.setAccessibleName(self.tr("AI set narrator status"))
        self.transition_table.setAccessibleName(self.tr("Transition analysis"))
        self.transition_details.setAccessibleName(self.tr("Selected transition details"))
        self.readiness_table.setAccessibleName(self.tr("Readiness checks"))
        self.back_button.setAccessibleName(self.tr("Back to build"))
        self.export_button.setAccessibleName(self.tr("Proceed to export"))

    def _setup_tab_order(self) -> None:
        """Define a logical keyboard tab order across primary controls."""
        self.setTabOrder(self.readiness_badge, self.recommendation_table)
        self.setTabOrder(self.recommendation_table, self.remove_track_button)
        self.setTabOrder(self.remove_track_button, self.save_to_playlists_button)
        self.setTabOrder(self.save_to_playlists_button, self.ai_narrate_button)
        self.setTabOrder(self.ai_narrate_button, self.ai_narrate_cancel_button)
        self.setTabOrder(self.ai_narrate_cancel_button, self.configure_ai_button)
        self.setTabOrder(self.configure_ai_button, self.engine_facts_button)
        self.setTabOrder(self.engine_facts_button, self.engine_facts_details)
        self.setTabOrder(self.engine_facts_details, self.compare_replacement_button)
        self.setTabOrder(self.compare_replacement_button, self.replacement_details)
        self.setTabOrder(self.replacement_details, self.transition_table)
        self.setTabOrder(self.transition_table, self.transition_details)
        self.setTabOrder(self.transition_details, self.readiness_table)
        self.setTabOrder(self.readiness_table, self.back_button)
        self.setTabOrder(self.back_button, self.export_button)

    def _apply_header_tooltips(self, table: QTableWidget, tooltips: dict[int, str]) -> None:
        for column_index, text in tooltips.items():
            header_item = table.horizontalHeaderItem(column_index)
            if header_item is None:
                header_item = QTableWidgetItem()
            if header_item is not None:
                header_item.setToolTip(self.tr(text))
                table.setHorizontalHeaderItem(column_index, header_item)

    def _connect_signals(self) -> None:
        self.back_button.clicked.connect(self.back_requested)
        self.export_button.clicked.connect(self.proceed_to_export_requested)
        self.save_to_playlists_button.clicked.connect(self.save_to_playlists_requested)
        self.ai_narrate_button.clicked.connect(self.ai_narrate_requested)
        self.configure_ai_button.clicked.connect(self.configure_ai_requested)
        self.ai_narrate_cancel_button.clicked.connect(self.ai_narrate_cancel_requested)
        self.engine_facts_button.toggled.connect(self.engine_facts_details.setVisible)
        self.compare_replacement_button.clicked.connect(self._compare_replacement)
        self.recommendation_table.itemSelectionChanged.connect(self._on_recommendation_selection_changed)
        self.remove_track_button.clicked.connect(self._on_remove_clicked)
        self.recommendation_table.itemDoubleClicked.connect(self._on_rec_double_clicked)
        self.transition_table.currentCellChanged.connect(self._update_transition_details)
        self.transition_table.itemSelectionChanged.connect(self._update_transition_details)
        self.transition_table.itemChanged.connect(self._on_transition_item_changed)
        self.transition_table.model().modelReset.connect(self._clear_transition_details)
        self.transition_table.model().rowsRemoved.connect(self._on_transition_rows_removed)

    def connect_signals(self, window: Any) -> None:
        self.back_requested.connect(lambda: window.workflow_tabs.setCurrentIndex(1))
        self.proceed_to_export_requested.connect(window._library_controller.on_proceed_to_export)
        self.ai_narrate_requested.connect(window.explain_ai_set)
        self.track_remove_requested.connect(window._library_controller.on_track_remove_requested)
        self.track_play_requested.connect(window._library_controller.on_track_play_requested)
        self.remove_without_selection_requested.connect(
            lambda: window.status_label.setText(self.tr("Select a track in the playlist before removing it"))
        )
        self.play_without_path_requested.connect(
            lambda: window.status_label.setText(self.tr("That track has no playable file path"))
        )

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, vm: ReviewViewModel, state: AppState, lightweight: bool = False) -> None:
        """Update all widgets from ViewModel data.

        Args:
            lightweight: If True, skip expensive recommendation table population
                        (used for non-visible tabs during state sync).
        """
        self._rendered_state = state
        context = (
            id(state.last_recommendation),
            id(state.last_dj_readiness_report),
            id(state.scanned_records),
            state.locked_paths,
            state.excluded_paths,
            state.settings.scoring,
            state.settings.loudness,
        )
        if context != self._replacement_context:
            self._replacement_context = context
            self.replacement_details.clear()
            self.replacement_details.setVisible(False)
        self.readiness_badge.setText(vm.readiness_badge_text(state))
        self.export_button.setEnabled(vm.can_export(state))
        self.save_to_playlists_button.setEnabled(state.last_recommendation is not None)
        # The narrative is cheap idempotent text from state, so it is re-applied on
        # every render (including lightweight ones) instead of needing a signature
        # cache. It is never cleared here: only a new recommendation invalidates it.
        facts = review_engine_facts(state)
        self.engine_facts_button.setEnabled(bool(facts))
        if self.engine_facts_details.toPlainText() != facts:
            self.engine_facts_details.setPlainText(facts)
        if not facts:
            self.engine_facts_button.setChecked(False)
        self.ai_narrate_cancel_button.setVisible(vm.is_narrating(state))
        self.ai_narrate_button.setEnabled(vm.narrate_button_enabled(state))
        if vm.is_narrating(state):
            # Only the busy text is render-owned. The success/failure message is
            # written by the controller and must survive the next idle render.
            self.ai_narrate_button.setText(self.tr("Narrando..."))
            self.ai_narrate_status.setText(self.tr("Narrating the set... this can take up to two minutes"))
        else:
            self.ai_narrate_button.setText(self.tr("Explícame este set"))
        narrative = vm.narrative_text(state)
        self.ai_narrative_label.setText(narrative)
        self.ai_narrative_label.setVisible(bool(narrative))
        if not lightweight:
            rows = vm.recommendation_rows(state)
            signature = _recommendation_rows_signature(rows)
            # The rowCount guard also covers controllers that clear the table
            # directly (e.g. library_controller._clear_scan_dependent_ui): a
            # cleared table no longer matches the signature even when the
            # ViewModel rows are unchanged, so the rebuild still happens.
            if signature != self._last_recommendation_signature or self.recommendation_table.rowCount() != len(rows):
                self._populate_recommendation_table(rows, self._track_reasons(state))
                self._last_recommendation_signature = signature
        # readiness_table and transition_table are populated imperatively by
        # _populate_dj_readiness_table / show_transition_review / clear_recommendation_review

    def _populate_readiness_table(self, rows: list[ReadinessCheckRow]) -> None:
        self.readiness_table.setRowCount(0)
        for row_data in rows:
            row = self.readiness_table.rowCount()
            self.readiness_table.insertRow(row)
            label_item = QTableWidgetItem(row_data.label)
            label_item.setToolTip(self.tr("Validation: {0}").format(row_data.label))
            status_item = QTableWidgetItem(row_data.status)
            status_item.setToolTip(self.tr("Status: {0}").format(row_data.status))
            detail_item = QTableWidgetItem(row_data.detail)
            detail_item.setToolTip(row_data.detail)
            self.readiness_table.setItem(row, 0, label_item)
            self.readiness_table.setItem(row, 1, status_item)
            self.readiness_table.setItem(row, 2, detail_item)

    def _selected_recommendation_paths(self) -> set[str]:
        """Paths (UserRole of column 0) of every currently selected row."""
        table = self.recommendation_table
        paths: set[str] = set()
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item is not None and item.isSelected():
                path = item.data(Qt.ItemDataRole.UserRole)
                if path:
                    paths.add(path)
        return paths

    def _restore_recommendation_selection(self, selected_paths: set[str], current_path: str | None) -> None:
        """Re-select previously selected paths that still exist after a rebuild.

        setRowCount(0) destroys selection and currentRow; restoring by path
        keeps the selection tied to the tracks, not to row positions, so a
        reordered playlist keeps the same tracks selected. Paths that no longer
        exist reset, which is correct: their data is gone.
        """
        if not selected_paths and not current_path:
            return
        table = self.recommendation_table
        matched_rows: list[int] = []
        restored_current_row: int | None = None
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            path = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
            if path and path in selected_paths:
                matched_rows.append(row)
                if path == current_path:
                    restored_current_row = row
        if restored_current_row is None:
            restored_current_row = matched_rows[0] if matched_rows else None
        # Set the current cell before selecting: setCurrentCell can clear a
        # freshly applied selection, so the selection must come last.
        if restored_current_row is not None:
            table.setCurrentCell(restored_current_row, 0)
        for row in matched_rows:
            for col in range(table.columnCount()):
                cell = table.item(row, col)
                if cell is not None:
                    cell.setSelected(True)

    def _track_reasons(self, state: AppState) -> dict[str, str]:
        """Build a per-path "why this track is here" tooltip from existing state.

        The DJ readiness report is playlist-level, so no per-track readiness
        status is claimed. Only data that already exists per track is surfaced:
        playlist position, opener/closer role, metadata completeness, and the
        warnings of the transitions that touch the track.

        Args:
            state: Application state carrying the last recommendation.

        Returns:
            Mapping of track path to a short multi-line reason. Tracks removed
            from the playlist are skipped, with positions renumbered to match
            the recommendation rows.
        """
        recommendation = state.last_recommendation
        if recommendation is None:
            return {}
        remaining = [t for t in recommendation.ordered_tracks if t.path not in state.playlist_removed_paths]
        warnings_by_path: dict[str, list[str]] = {}
        for transition in recommendation.transition_scores:
            for path in (transition.left_path, transition.right_path):
                warnings_by_path.setdefault(path, []).extend(transition.warnings)
        total = len(remaining)
        reasons: dict[str, str] = {}
        for position, track in enumerate(remaining, start=1):
            lines = [self.tr("Track #{0} of {1}").format(position, total)]
            if total > 1 and position == 1:
                lines.append(self.tr("Playlist opener"))
            elif total > 1 and position == total:
                lines.append(self.tr("Playlist closer"))
            if track.metadata_status != "complete" or track.missing_required_fields:
                missing = ", ".join(track.missing_required_fields) or track.metadata_status
                lines.append(self.tr("Incomplete metadata: {0}").format(missing))
            else:
                lines.append(self.tr("Metadata complete: BPM, key, and energy available"))
            warnings = warnings_by_path.get(track.path, [])
            if warnings:
                lines.append(self.tr("Transition warnings:"))
                lines.extend("• " + warning for warning in warnings)
            else:
                lines.append(self.tr("No warnings in adjacent transitions"))
            reasons[track.path] = "\n".join(lines)
        return reasons

    def _populate_recommendation_table(
        self, rows: list[RecommendationRow], reasons: dict[str, str] | None = None
    ) -> None:
        """Populate recommendation rows; per-track reasons replace the generic tooltip when available."""
        previous_selected_paths = self._selected_recommendation_paths()
        current_row_item = self.recommendation_table.item(self.recommendation_table.currentRow(), 0)
        previous_current_path = (
            current_row_item.data(Qt.ItemDataRole.UserRole) if current_row_item is not None else None
        )
        self.recommendation_table.setRowCount(0)
        for row_data in rows:
            row = self.recommendation_table.rowCount()
            self.recommendation_table.insertRow(row)
            values = [
                str(row_data.position),
                row_data.title,
                row_data.artist,
                row_data.bpm,
                row_data.camelot_key,
                row_data.energy,
                row_data.spectral_color,
            ]
            tooltips = [
                (reasons or {}).get(row_data.path) or self.tr("Track #{0} in playlist").format(row_data.position),
                row_data.title,
                row_data.artist,
                self.tr("BPM: {0}").format(row_data.bpm),
                self.tr("Camelot key: {0}").format(row_data.camelot_key),
                self.tr("Energy level: {0}").format(row_data.energy),
                self.tr("Spectral color: {0}").format(row_data.spectral_color),
            ]
            for col, (value, tip) in enumerate(zip(values, tooltips, strict=True)):
                item = QTableWidgetItem(value)
                item.setToolTip(tip)
                self.recommendation_table.setItem(row, col, item)
            # Store path as UserRole on col 0 for removal and play actions
            position_item = self.recommendation_table.item(row, 0)
            if position_item is not None:
                position_item.setData(Qt.ItemDataRole.UserRole, row_data.path)
        self._restore_recommendation_selection(previous_selected_paths, previous_current_path)

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _clear_transition_details(self) -> None:
        self._selected_transition_context = None
        self.transition_details.clear()
        self.transition_details.setVisible(False)

    def _on_transition_rows_removed(self) -> None:
        self.transition_table.clearSelection()
        self._clear_transition_details()

    def _transition_context(self) -> tuple[str, ...]:
        row = self.transition_table.currentRow()
        return tuple(
            item.text() if (item := self.transition_table.item(row, column)) is not None else "" for column in (0, 1, 2)
        )

    def _on_transition_item_changed(self, item: QTableWidgetItem) -> None:
        if item.row() != self.transition_table.currentRow():
            return
        if (
            self._selected_transition_context is not None
            and self._transition_context() != self._selected_transition_context
        ):
            # Imperative repopulation can replace a row without changing its
            # index. Never silently attach the old selection to a new pair.
            self.transition_table.clearSelection()
            self.transition_table.setCurrentCell(-1, -1)
            self._clear_transition_details()
            return
        self._update_transition_details()

    def _update_transition_details(self) -> None:
        table = self.transition_table
        current = table.currentItem()
        if current is None or not current.isSelected():
            self._clear_transition_details()
            return
        context = self._transition_context()
        row = table.currentRow()
        score_column = current.column() if 3 <= current.column() <= 9 else 9
        score = table.item(row, score_column)
        warning = table.item(row, 10)
        if not all(context) or score is None or warning is None:
            self._clear_transition_details()
            return
        warning_text = warning.toolTip() or warning.text() or self.tr("No warnings for this transition")
        header = table.horizontalHeaderItem(score_column)
        explanation = score.toolTip() or self.tr("No score explanation available")
        text = "\n".join(
            [
                self.tr("Transition #{0}: {1} → {2}").format(*context),
                self.tr("Warnings: {0}").format(warning_text),
                f"{header.text()}: {score.text()} — {explanation}",
            ]
        )
        self._selected_transition_context = context
        # Preserve the text cursor/selection across idempotent state syncs.
        if text != self.transition_details.toPlainText():
            self.transition_details.setPlainText(text)
        self.transition_details.setVisible(True)

    def _on_recommendation_selection_changed(self) -> None:
        self.remove_track_button.setEnabled(bool(self.recommendation_table.selectedItems()))
        self.compare_replacement_button.setEnabled(bool(self._selected_replacement_path()))
        self.replacement_details.clear()
        self.replacement_details.setVisible(False)

    def _selected_replacement_path(self) -> str:
        rows = {item.row() for item in self.recommendation_table.selectedItems()}
        if len(rows) != 1:
            return ""
        item = self.recommendation_table.item(next(iter(rows)), 0)
        return str(item.data(Qt.ItemDataRole.UserRole) or "") if item is not None else ""

    def _compare_replacement(self) -> None:
        path = self._selected_replacement_path()
        self.replacement_details.setPlainText(preview_engine_replacement(self._rendered_state, path))
        self.replacement_details.setVisible(True)

    def _on_remove_clicked(self) -> None:
        selected = self.recommendation_table.selectedItems()
        if not selected:
            # Surface guidance instead of failing silently: the button looks
            # dead otherwise when nothing is selected.
            self.remove_without_selection_requested.emit()
            return
        row = self.recommendation_table.currentRow()
        path_item = self.recommendation_table.item(row, 0)
        path = path_item.data(Qt.ItemDataRole.UserRole) if path_item is not None else None
        if path:
            self.track_remove_requested.emit(path)
        else:
            self.remove_without_selection_requested.emit()

    def _on_rec_double_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        path_item = self.recommendation_table.item(row, 0)
        path = path_item.data(Qt.ItemDataRole.UserRole) if path_item is not None else None
        if path:
            self.track_play_requested.emit(path)
        else:
            self.play_without_path_requested.emit()
