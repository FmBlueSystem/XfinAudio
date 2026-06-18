from __future__ import annotations

from typing import Any, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from xfinaudio.desktop.table_populators import (
    populate_dj_readiness_table,
    populate_library_table,
    populate_prep_copilot_table,
    populate_recommendation_table,
    populate_serato_export_history_table,
    populate_transition_review_table,
)
from xfinaudio.exporting.explainability import PlaylistExplanation, TrackExplanation, TransitionExplanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.dj_readiness import DjReadinessCheck, DjReadinessReport
from xfinaudio.recommendation.prep_copilot import DJSetIntent


class SortAwareTestItem(QTableWidgetItem):
    def __init__(self, display_value: str, sort_value: object | None = None) -> None:
        super().__init__(display_value)
        self.sort_value = display_value.casefold() if sort_value is None else sort_value

    def __lt__(self, other: QTableWidgetItem) -> bool:
        other_value = getattr(other, "sort_value", other.text().casefold())
        return cast(Any, self.sort_value) < cast(Any, other_value)


def ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)


def item_factory(display_value: str, sort_value: object | None = None) -> QTableWidgetItem:
    return SortAwareTestItem(display_value, sort_value)


def format_missing_metadata(record: TrackRecord) -> str:
    labels = {"bpm": "BPM", "camelot_key": "Camelot key", "energy_level": "energy level"}
    return ", ".join(labels[field] for field in record.missing_required_fields)


def format_track_tags(record: TrackRecord) -> str:
    return ", ".join(record.tags)


def format_spectral_color(record: TrackRecord) -> str:
    return "🔴 RED" if record.title == "High" else ""


def format_warning(raw_warning: str) -> str:
    return f"formatted:{raw_warning}"


def test_populate_library_table_uses_format_genre_cell_when_provided(tmp_path) -> None:
    """When format_genre_cell is provided, the genre column renders the
    canonical (enriched) genre plus a confidence badge instead of the raw
    file-tag genre."""
    from xfinaudio.genre.models import GenreDecision, GenreProvenance

    ensure_app()
    table = QTableWidget()
    table.setColumnCount(12)

    decision = GenreDecision(
        primary="Tech House",
        top_n=("Tech House",),
        confidence=0.9,
        low_confidence=False,
        provenance=GenreProvenance(),
    )
    enriched = TrackRecord(
        path=str(tmp_path / "enriched.flac"),
        title="Enriched",
        genre="Electronica",  # raw tag, misleading
        genre_decision=decision,
    )
    not_enriched = TrackRecord(
        path=str(tmp_path / "raw.flac"),
        title="Raw",
        genre="House",
    )

    def genre_cell(record: TrackRecord) -> str:
        if record.genre_decision is not None:
            return f"CANONICAL: {record.genre_decision.primary}"
        return f"RAW: {record.genre or ''}"

    populate_library_table(
        table,
        [enriched, not_enriched],
        item_factory=item_factory,
        format_missing_metadata=format_missing_metadata,
        format_track_tags=format_track_tags,
        format_spectral_color=format_spectral_color,
        format_genre_cell=genre_cell,
    )

    assert table.item(0, 8).text() == "CANONICAL: Tech House"
    assert table.item(1, 8).text() == "RAW: House"


def test_populate_library_table_sets_genre_tooltip_when_provided(tmp_path) -> None:
    ensure_app()
    table = QTableWidget()
    table.setColumnCount(12)

    enriched = TrackRecord(
        path=str(tmp_path / "enriched.flac"),
        title="Enriched",
        genre="Electronica",
        genre_decision=__import__(
            "xfinaudio.genre.models", fromlist=["GenreDecision", "GenreProvenance"]
        ).GenreDecision(
            primary="Tech House",
            top_n=("Tech House",),
            confidence=0.9,
            low_confidence=False,
            provenance=__import__("xfinaudio.genre.models", fromlist=["GenreProvenance"]).GenreProvenance(),
        ),
    )
    no_decision = TrackRecord(
        path=str(tmp_path / "raw.flac"),
        title="Raw",
        genre="House",
    )

    def genre_tooltip(record: TrackRecord) -> str:
        if record.genre_decision is None:
            return ""
        return f"Canonical: {record.genre_decision.primary}\nConfidence: {record.genre_decision.confidence:.2f}"

    populate_library_table(
        table,
        [enriched, no_decision],
        item_factory=item_factory,
        format_missing_metadata=format_missing_metadata,
        format_track_tags=format_track_tags,
        format_spectral_color=format_spectral_color,
        format_genre_cell=lambda r: r.genre or "",
        format_genre_tooltip=genre_tooltip,
    )

    # The enriched row carries the tooltip; the row without a decision has none.
    assert table.item(0, 8).toolTip() != ""
    assert "Tech House" in table.item(0, 8).toolTip()
    assert "0.90" in table.item(0, 8).toolTip()
    assert table.item(1, 8).toolTip() == ""


def test_populate_library_table_default_genre_cell_matches_raw_genre(tmp_path) -> None:
    """Without format_genre_cell, the genre column still shows the raw tag
    (preserves pre-enrichment behavior)."""
    ensure_app()
    table = QTableWidget()
    table.setColumnCount(12)
    record = TrackRecord(
        path=str(tmp_path / "x.flac"),
        title="X",
        genre="Disco",
    )

    populate_library_table(
        table,
        [record],
        item_factory=item_factory,
        format_missing_metadata=format_missing_metadata,
        format_track_tags=format_track_tags,
        format_spectral_color=format_spectral_color,
    )

    assert table.item(0, 8).text() == "Disco"
    assert table.item(0, 8).toolTip() == ""


def test_populate_library_table_writes_columns_mapping_and_numeric_bpm_sort(tmp_path) -> None:
    ensure_app()
    table = QTableWidget()
    table.setColumnCount(12)
    records = [
        TrackRecord(
            path=str(tmp_path / "high.flac"),
            title="High",
            artist="Artist A",
            bpm=128,
            camelot_key="8A",
            energy_level=7,
            genre="Disco",
            tags=["Peak", "Vocal"],
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(tmp_path / "low.flac"),
            title="Low",
            artist="Artist B",
            bpm=95,
            camelot_key="9A",
            energy_level=3,
            genre="House",
            tags=["Warmup"],
            metadata_status="incomplete",
            missing_required_fields=["camelot_key", "energy_level"],
        ),
        TrackRecord(path=str(tmp_path / "mid.flac"), title="Mid", bpm=104, metadata_status="complete"),
    ]

    records_by_path = populate_library_table(
        table,
        records,
        item_factory=item_factory,
        format_missing_metadata=format_missing_metadata,
        format_track_tags=format_track_tags,
        format_spectral_color=format_spectral_color,
    )

    assert table.rowCount() == 3
    assert [table.item(0, column).text() for column in range(12)] == [
        "High",
        "Artist A",
        "128",
        "8A",
        "7",
        "—",
        "🔴 RED",
        "",
        "Disco",
        "complete",
        "▶",
        str(tmp_path / "high.flac"),
    ]
    assert [table.item(1, column).text() for column in range(12)] == [
        "Low",
        "Artist B",
        "95",
        "9A",
        "3",
        "—",
        "",
        "Camelot key, energy level",
        "House",
        "incomplete",
        "▶",
        str(tmp_path / "low.flac"),
    ]
    assert records_by_path == {record.path: record for record in records}

    table.sortItems(2, Qt.SortOrder.AscendingOrder)

    assert [table.item(row, 0).text() for row in range(table.rowCount())] == ["Low", "Mid", "High"]


def test_populate_recommendation_table_formats_transitions_without_mutating_warnings(tmp_path) -> None:
    ensure_app()
    table = QTableWidget()
    table.setColumnCount(11)
    left = TrackRecord(
        path=str(tmp_path / "left.flac"),
        title="Left",
        artist="Artist L",
        bpm=100,
        camelot_key="7A",
        energy_level=4,
        genre="Disco",
        tags=["Warmup"],
        metadata_status="complete",
    )
    right = TrackRecord(
        path=str(tmp_path / "right.flac"),
        title="Right",
        artist="Artist R",
        bpm=123.5,
        camelot_key="8A",
        energy_level=6,
        genre="House",
        tags=["Peak", "Vocal"],
        metadata_status="complete",
    )
    raw_warnings = ["left missing required metadata: camelot_key", "invalid Camelot key"]
    explanation = PlaylistExplanation(
        strategy="harmonic_journey",
        optimizer="greedy",
        track_count=2,
        transition_count=1,
        total_score=0.8123,
        warnings=[],
        transitions=[
            TransitionExplanation(
                order=1,
                left=TrackExplanation(path=left.path, title=left.title, metadata_status=left.metadata_status),
                right=TrackExplanation(path=right.path, title=right.title, metadata_status=right.metadata_status),
                component_scores={},
                final_score=0.8123,
                warnings=list(raw_warnings),
                explanations=[],
            )
        ],
    )

    populate_recommendation_table(
        table,
        [left, right],
        "harmonic_journey",
        explanation,
        item_factory=item_factory,
        format_track_tags=format_track_tags,
        format_warning=format_warning,
    )

    assert table.rowCount() == 2
    assert [table.item(0, column).text() for column in range(11)] == [
        "Left",
        "Artist L",
        "100",
        "7A",
        "4",
        "Disco",
        "Warmup",
        "harmonic_journey",
        str(tmp_path / "left.flac"),
        "",
        "",
    ]
    assert [table.item(1, column).text() for column in range(11)] == [
        "Right",
        "Artist R",
        "123.5",
        "8A",
        "6",
        "House",
        "Peak, Vocal",
        "harmonic_journey",
        str(tmp_path / "right.flac"),
        "0.812",
        "formatted:left missing required metadata: camelot_key; formatted:invalid Camelot key",
    ]
    assert explanation.transitions[0].warnings == raw_warnings


# ---------------------------------------------------------------------------
# T4: migrated from test_main_window — no window construction needed
# ---------------------------------------------------------------------------

_READINESS_STATUS_LABELS = {"ready": "Ready", "needs_review": "Needs Review", "blocked": "Blocked"}
_READINESS_STATUS_COLORS = {"ready": "#1fd16a", "needs_review": "#ffb000", "blocked": "#ff4d4f"}
_READINESS_STATUS_TOOLTIPS = {
    "ready": "Ready: no action needed",
    "needs_review": "Needs Review: inspect before export",
    "blocked": "Blocked: fix before export",
}


def _item_text(table: QTableWidget, row: int, column: int) -> str:
    item = table.item(row, column)
    assert item is not None
    return item.text()


def _item(table: QTableWidget, row: int, column: int) -> QTableWidgetItem:
    item = table.item(row, column)
    assert item is not None
    return item


def test_populate_dj_readiness_table_colors_status_cells() -> None:
    ensure_app()
    table = QTableWidget()
    table.setColumnCount(3)
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

    populate_dj_readiness_table(
        table,
        report,
        item_factory=item_factory,
        readiness_status_labels=_READINESS_STATUS_LABELS,
        readiness_status_colors=_READINESS_STATUS_COLORS,
        readiness_status_tooltips=_READINESS_STATUS_TOOLTIPS,
    )

    status_by_check = {_item_text(table, row, 0): _item(table, row, 1) for row in range(table.rowCount())}

    assert status_by_check["BPM continuity"].text() == "Blocked"
    assert status_by_check["BPM continuity"].background().color().name() == "#ff4d4f"
    assert status_by_check["BPM continuity"].toolTip() == "Blocked: fix before export"
    assert status_by_check["Transition warnings"].text() == "Needs Review"
    assert status_by_check["Transition warnings"].background().color().name() == "#ffb000"
    assert status_by_check["Transition warnings"].toolTip() == "Needs Review: inspect before export"
    assert status_by_check["Required metadata"].text() == "Ready"
    assert status_by_check["Required metadata"].background().color().name() == "#1fd16a"
    assert status_by_check["Required metadata"].toolTip() == "Ready: no action needed"


# ---------------------------------------------------------------------------
# T5: new tests for the 3 remaining free functions
# ---------------------------------------------------------------------------


def test_populate_transition_review_table_renders_scores_and_warnings(tmp_path) -> None:
    ensure_app()
    table = QTableWidget()
    table.setColumnCount(9)

    left = TrackExplanation(path=str(tmp_path / "left.flac"), title="Left Track", metadata_status="complete")
    right = TrackExplanation(path=str(tmp_path / "right.flac"), title="Right Track", metadata_status="complete")
    explanation = PlaylistExplanation(
        strategy="harmonic_journey",
        optimizer="greedy",
        track_count=2,
        transition_count=1,
        total_score=0.75,
        warnings=[],
        transitions=[
            TransitionExplanation(
                order=1,
                left=left,
                right=right,
                component_scores={"key_score": 0.9, "bpm_score": 0.8, "energy_score": 0.7, "tag_score": 0.6},
                final_score=0.75,
                warnings=["timing concern"],
                explanations=[],
            )
        ],
    )

    from xfinaudio.desktop.rendering import (
        _component_score,
        _format_review_score,
        _score_sort_value,
        _track_review_name,
        format_recommendation_warning,
    )

    populate_transition_review_table(
        table,
        explanation,
        item_factory=item_factory,
        format_review_score=_format_review_score,
        component_score=_component_score,
        score_sort_value=_score_sort_value,
        track_review_name=_track_review_name,
        format_warning=format_recommendation_warning,
    )

    assert table.rowCount() == 1
    row_values = [table.item(0, col).text() for col in range(9)]
    # col 0: order; col 1: left name; col 2: right name; col 8: warnings
    assert row_values[0] == "1"
    assert "Left Track" in row_values[1]
    assert "Right Track" in row_values[2]
    # col 8: formatted warning text
    assert "timing concern" in row_values[8]
    # numeric sort value on col 7 (final score) should be a float, not a string
    final_score_item = table.item(0, 7)
    assert final_score_item is not None
    assert hasattr(final_score_item, "sort_value")


def test_populate_prep_copilot_table_colors_readiness_status(tmp_path) -> None:
    ensure_app()
    from xfinaudio.recommendation.prep_copilot import build_prep_copilot_plan

    table = QTableWidget()
    table.setColumnCount(4)

    records = [
        TrackRecord(
            path=str(tmp_path / f"{i}.flac"),
            title=f"Track {i}",
            bpm=120 + i,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["House"],
            metadata_status="complete",
        )
        for i in range(5)
    ]
    intent = DJSetIntent(name="test", target_track_count=3)
    plan = build_prep_copilot_plan(records, intent)

    populate_prep_copilot_table(
        table,
        plan,
        item_factory=item_factory,
        readiness_status_labels=_READINESS_STATUS_LABELS,
        readiness_status_colors=_READINESS_STATUS_COLORS,
    )

    assert table.rowCount() == 3
    variant_names = [table.item(row, 0).text() for row in range(3)]
    assert variant_names == ["safe", "balanced", "adventurous"]
    # All statuses should be colored with one of the known readiness colors
    for row in range(3):
        status_item = table.item(row, 1)
        assert status_item is not None
        assert status_item.background().color().name() in _READINESS_STATUS_COLORS.values()


def test_populate_serato_export_history_table_renders_rows() -> None:
    ensure_app()
    table = QTableWidget()
    table.setColumnCount(6)

    history = [
        {
            "time": "12:00:00",
            "strategy": "build",
            "tracks": "3",
            "path": "/music/set.crate",
            "readiness_json_path": "/music/readiness.json",
            "readiness_csv_path": "/music/readiness.csv",
        }
    ]

    populate_serato_export_history_table(
        table,
        history,
        item_factory=item_factory,
    )

    assert table.rowCount() == 1
    assert table.item(0, 0).text() == "12:00:00"
    assert table.item(0, 1).text() == "build"
    assert table.item(0, 2).text() == "3"
    assert table.item(0, 3).text() == "/music/set.crate"
    assert table.item(0, 3).toolTip() == "/music/set.crate"
    assert table.item(0, 4).text() == "/music/readiness.json"
    assert table.item(0, 4).toolTip() == "/music/readiness.json"
    assert table.item(0, 5).text() == "/music/readiness.csv"
    assert table.item(0, 5).toolTip() == "/music/readiness.csv"
