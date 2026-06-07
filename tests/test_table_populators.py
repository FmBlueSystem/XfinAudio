from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from xfinaudio.desktop.table_populators import populate_library_table, populate_recommendation_table
from xfinaudio.exporting.explainability import PlaylistExplanation, TrackExplanation, TransitionExplanation
from xfinaudio.library.models import TrackRecord


class SortAwareTestItem(QTableWidgetItem):
    def __init__(self, display_value: str, sort_value: object | None = None) -> None:
        super().__init__(display_value)
        self.sort_value = display_value.casefold() if sort_value is None else sort_value

    def __lt__(self, other: QTableWidgetItem) -> bool:
        other_value = getattr(other, "sort_value", other.text().casefold())
        return self.sort_value < other_value


def ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def item_factory(display_value: str, sort_value: object | None = None) -> QTableWidgetItem:
    return SortAwareTestItem(display_value, sort_value)


def format_missing_metadata(record: TrackRecord) -> str:
    labels = {"bpm": "BPM", "camelot_key": "Camelot key", "energy_level": "energy level"}
    return ", ".join(labels[field] for field in record.missing_required_fields)


def format_track_tags(record: TrackRecord) -> str:
    return ", ".join(record.tags)


def format_warning(raw_warning: str) -> str:
    return f"formatted:{raw_warning}"


def test_populate_library_table_writes_columns_mapping_and_numeric_bpm_sort(tmp_path) -> None:
    ensure_app()
    table = QTableWidget()
    table.setColumnCount(10)
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
    )

    assert table.rowCount() == 3
    assert [table.item(0, column).text() for column in range(10)] == [
        "High",
        "Artist A",
        "128",
        "8A",
        "7",
        "",
        "Disco",
        "Peak, Vocal",
        "complete",
        str(tmp_path / "high.flac"),
    ]
    assert [table.item(1, column).text() for column in range(10)] == [
        "Low",
        "Artist B",
        "95",
        "9A",
        "3",
        "Camelot key, energy level",
        "House",
        "Warmup",
        "incomplete",
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
