import csv
import json
from io import StringIO

import pytest

from xfinaudio.exporting.explainability import build_playlist_explanation
from xfinaudio.exporting.playlist_exporters import (
    default_exporter_registry,
    export_playlist_csv,
    export_playlist_json,
    export_playlist_m3u,
    export_quality_report_json,
    write_playlist_json,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.recommendation_quality import build_quality_report
from xfinaudio.recommendation.playlist_service import recommend_playlist


def complete_track(path: str, title: str, bpm: float, key: str, energy: int) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=title,
        artist=f"Artist {title}",
        bpm=bpm,
        camelot_key=key,
        energy_level=energy,
        metadata_status="complete",
    )


def sample_recommendation():
    return recommend_playlist(
        [
            complete_track("/music/a.flac", "A", 124.0, "8A", 5),
            complete_track("/music/b.flac", "B", 125.0, "8A", 6),
        ],
        "harmonic_journey",
    )


def test_export_playlist_json_is_deterministic_with_ordered_tracks_and_explanations() -> None:
    recommendation = sample_recommendation()

    first = export_playlist_json(recommendation)
    second = export_playlist_json(recommendation)

    assert first == second
    payload = json.loads(first)
    assert [track["path"] for track in payload["tracks"]] == [track.path for track in recommendation.ordered_tracks]
    assert payload["explanation"] == build_playlist_explanation(recommendation).model_dump(mode="json")
    assert recommendation.build_log is not None
    assert payload["build_log"] == recommendation.build_log.model_dump(mode="json")


def test_export_playlist_csv_uses_stable_columns_and_track_order() -> None:
    recommendation = sample_recommendation()

    rows = list(csv.DictReader(StringIO(export_playlist_csv(recommendation))))

    assert rows[0].keys() == {"order", "path", "title", "artist", "bpm", "camelot_key", "energy_level", "status"}
    assert [row["order"] for row in rows] == ["1", "2"]
    assert [row["path"] for row in rows] == [track.path for track in recommendation.ordered_tracks]
    assert rows[0]["bpm"] == "124"


def test_export_playlist_m3u_preserves_track_order() -> None:
    recommendation = sample_recommendation()

    content = export_playlist_m3u(recommendation)

    assert content.splitlines() == ["#EXTM3U", *[track.path for track in recommendation.ordered_tracks]]


def test_write_playlist_json_writes_only_caller_provided_target(tmp_path) -> None:
    recommendation = sample_recommendation()
    target = tmp_path / "playlist.json"

    written = write_playlist_json(recommendation, target)

    assert written == target
    assert target.read_text(encoding="utf-8") == export_playlist_json(recommendation)


def test_default_exporter_registry_lists_playlist_formats() -> None:
    registry = default_exporter_registry()

    assert registry.available_formats() == ["json", "csv", "m3u"]


def test_exporter_registry_rejects_unknown_format() -> None:
    registry = default_exporter_registry()

    with pytest.raises(ValueError, match="Unknown playlist export format"):
        registry.get("pdf")


def test_exporter_registry_export_matches_existing_function_output() -> None:
    recommendation = sample_recommendation()
    registry = default_exporter_registry()

    assert registry.export("json", recommendation) == export_playlist_json(recommendation)


def test_export_quality_report_json_is_deterministic() -> None:
    report = build_quality_report(sample_recommendation())

    first = export_quality_report_json(report)
    second = export_quality_report_json(report)

    assert first == second
    assert json.loads(first) == report.model_dump(mode="json")
