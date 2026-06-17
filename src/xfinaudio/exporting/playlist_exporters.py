"""Deterministic playlist exporters."""

from __future__ import annotations

import csv
import json
from collections.abc import Callable
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from xfinaudio.exporting.explainability import build_playlist_explanation
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation

CSV_COLUMNS = ["order", "path", "title", "artist", "bpm", "camelot_key", "energy_level", "status"]


@dataclass(frozen=True)
class PlaylistExporter:
    """Registered playlist export format."""

    name: str
    extension: str
    media_type: str
    export: Callable[[PlaylistRecommendation], str]


class ExporterRegistry:
    """Registry seam for playlist exporters."""

    def __init__(self, exporters: list[PlaylistExporter] | tuple[PlaylistExporter, ...] = ()) -> None:
        self._exporters: dict[str, PlaylistExporter] = {}
        for exporter in exporters:
            self.register(exporter)

    def register(self, exporter: PlaylistExporter) -> None:
        """Register a playlist exporter by format name."""
        if exporter.name in self._exporters:
            raise ValueError(f"Duplicate playlist export format: {exporter.name}")
        self._exporters[exporter.name] = exporter

    def available_formats(self) -> list[str]:
        """Return supported playlist export formats in registration order."""
        return list(self._exporters)

    def get(self, name: str) -> PlaylistExporter:
        """Return an exporter by format name."""
        try:
            return self._exporters[name]
        except KeyError as exc:
            raise ValueError(f"Unknown playlist export format: {name}") from exc

    def export(self, name: str, recommendation: PlaylistRecommendation) -> str:
        """Export a recommendation through a registered exporter."""
        return self.get(name).export(recommendation)


def export_playlist_json(recommendation: PlaylistRecommendation) -> str:
    """Return a deterministic JSON export for a playlist recommendation."""
    build_log = recommendation.build_log.model_dump(mode="json") if recommendation.build_log is not None else None
    payload = {
        "strategy": recommendation.strategy.name,
        "optimizer": recommendation.optimizer,
        "total_score": recommendation.total_score,
        "warnings": list(recommendation.warnings),
        "tracks": [_track_payload(index, track) for index, track in enumerate(recommendation.ordered_tracks, start=1)],
        "explanation": build_playlist_explanation(recommendation).model_dump(mode="json"),
        "build_log": build_log,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def export_playlist_csv(recommendation: PlaylistRecommendation) -> str:
    """Return a CSV export with stable columns and playlist order."""
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for index, track in enumerate(recommendation.ordered_tracks, start=1):
        writer.writerow(_track_payload(index, track))
    return output.getvalue()


def export_playlist_m3u(recommendation: PlaylistRecommendation) -> str:
    """Return an M3U playlist preserving recommended track order."""
    return "\n".join(["#EXTM3U", *[track.path for track in recommendation.ordered_tracks]]) + "\n"


def export_quality_report_json(report: RecommendationQualityReport) -> str:
    """Return a deterministic JSON export for recommendation quality metrics."""
    return json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def default_exporter_registry() -> ExporterRegistry:
    """Return the built-in playlist exporter registry."""
    return ExporterRegistry(
        (
            PlaylistExporter("json", ".json", "application/json", export_playlist_json),
            PlaylistExporter("csv", ".csv", "text/csv", export_playlist_csv),
            PlaylistExporter("m3u", ".m3u", "audio/x-mpegurl", export_playlist_m3u),
        )
    )


def write_playlist_json(recommendation: PlaylistRecommendation, target: str | Path) -> Path:
    """Write JSON export to a caller-provided target file."""
    return _write_text(target, export_playlist_json(recommendation))


def write_playlist_csv(recommendation: PlaylistRecommendation, target: str | Path) -> Path:
    """Write CSV export to a caller-provided target file."""
    return _write_text(target, export_playlist_csv(recommendation))


def write_playlist_m3u(recommendation: PlaylistRecommendation, target: str | Path) -> Path:
    """Write M3U export to a caller-provided target file."""
    return _write_text(target, export_playlist_m3u(recommendation))


def _track_payload(order: int, track: TrackRecord) -> dict[str, object]:
    return {
        "order": order,
        "path": track.path,
        "title": track.title or "",
        "artist": track.artist or "",
        "bpm": "" if track.bpm is None else f"{track.bpm:g}",
        "camelot_key": track.camelot_key or "",
        "energy_level": "" if track.energy_level is None else track.energy_level,
        "status": track.metadata_status,
    }


def _write_text(target: str | Path, content: str) -> Path:
    target_path = Path(target)
    target_path.write_text(content, encoding="utf-8")
    return target_path


__all__ = [
    "CSV_COLUMNS",
    "ExporterRegistry",
    "PlaylistExporter",
    "default_exporter_registry",
    "export_playlist_csv",
    "export_playlist_json",
    "export_playlist_m3u",
    "export_quality_report_json",
    "write_playlist_csv",
    "write_playlist_json",
    "write_playlist_m3u",
]
