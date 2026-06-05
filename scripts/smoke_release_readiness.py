#!/usr/bin/env python3
"""Post-MVP release readiness smoke workflow for XfinAudio."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService  # noqa: E402
from xfinaudio.exporting.playlist_exporters import (  # noqa: E402
    default_exporter_registry,
    export_quality_report_json,
)
from xfinaudio.exporting.serato_crate import plan_serato_crate_export  # noqa: E402
from xfinaudio.library.models import TrackRecord  # noqa: E402
from xfinaudio.library.track_repository import TrackRepository  # noqa: E402


class StaticScanService:
    """Fixture scan service used to exercise the workflow without reading audio files."""

    def __init__(self, records: list[TrackRecord]) -> None:
        self._records = records

    def scan(self, folder: Path) -> list[TrackRecord]:
        """Return deterministic fixture records without touching the requested folder."""
        return self._records


def main() -> int:
    """Run the release readiness smoke workflow and print a concise pass checklist."""
    with tempfile.TemporaryDirectory(prefix="xfinaudio-release-smoke-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        db_path = temp_dir / "xfinaudio-smoke.sqlite3"
        repository = TrackRepository(db_path)
        print("PASS temp app database created")

        records = _build_track_fixtures()
        repository.save_scan_results(records)
        persisted_records = repository.list_tracks()
        _require(len(persisted_records) == len(records), "track repository did not round-trip fixtures")
        _require(all(record.metadata_status == "complete" for record in persisted_records), "fixtures must be complete")
        print("PASS track repository saved and listed fixtures")

        workflow = PlaylistWorkflowService(scan_service=StaticScanService(records), repository=repository)
        recommendation_result = workflow.recommend(persisted_records, "harmonic_journey")
        _require(len(recommendation_result.recommendation.ordered_tracks) == len(records), "recommendation lost tracks")
        _require(
            recommendation_result.quality_report.track_count == len(records),
            "quality report track count mismatch",
        )
        print("PASS playlist workflow recommendation built")

        registry = default_exporter_registry()
        json_export = registry.export("json", recommendation_result.recommendation)
        csv_export = registry.export("csv", recommendation_result.recommendation)
        m3u_export = registry.export("m3u", recommendation_result.recommendation)
        csv_header = "order,path,title,artist,bpm,camelot_key,energy_level,status\n"
        _require(json.loads(json_export)["tracks"], "JSON export did not include tracks")
        _require(csv_export.startswith(csv_header), "CSV header mismatch")
        _require(m3u_export.startswith("#EXTM3U\n"), "M3U header mismatch")
        print("PASS playlist exporters produced JSON/CSV/M3U strings")

        quality_json = export_quality_report_json(recommendation_result.quality_report)
        _require(json.loads(quality_json)["track_count"] == len(records), "quality JSON track count mismatch")
        print("PASS quality report JSON built")

        serato_relative_paths = [
            f"Music/Release Smoke/{Path(track.path).name}"
            for track in recommendation_result.recommendation.ordered_tracks
        ]
        serato_plan = plan_serato_crate_export(
            "XfinAudio Release Smoke",
            serato_relative_paths,
            temp_dir / "serato-fixture-root",
        )
        preview = serato_plan.preview()
        _require(preview["will_write"] is False, "Serato plan must be dry-run only")
        _require(not serato_plan.target_path.exists(), "Serato dry-run unexpectedly wrote a crate file")
        _require(serato_plan.track_count == len(records), "Serato plan track count mismatch")
        print("PASS Serato crate dry-run plan built without writing")

    print("PASS release readiness smoke completed")
    return 0


def _build_track_fixtures() -> list[TrackRecord]:
    """Build deterministic complete metadata records without creating audio files."""
    fixture_root = "/fixtures/mixed-in-key-release-smoke"
    return [
        TrackRecord(
            path=f"{fixture_root}/01-neon-arrival.aiff",
            title="Neon Arrival",
            artist="Xfin Fixture",
            bpm=124.0,
            camelot_key="8A",
            energy_level=5,
            genre="House",
            tags=["groove", "warm"],
            metadata_status="complete",
            source_fields={"bpm": "TBPM", "camelot_key": "TKEY", "energy_level": "COMM:Songs-DB_Custom1"},
            raw_metadata={"fixture": "release-smoke"},
        ),
        TrackRecord(
            path=f"{fixture_root}/02-lunar-bridge.aiff",
            title="Lunar Bridge",
            artist="Xfin Fixture",
            bpm=125.0,
            camelot_key="8B",
            energy_level=6,
            genre="House",
            tags=["groove", "lift"],
            metadata_status="complete",
            source_fields={"bpm": "TBPM", "camelot_key": "TKEY", "energy_level": "COMM:Songs-DB_Custom1"},
            raw_metadata={"fixture": "release-smoke"},
        ),
        TrackRecord(
            path=f"{fixture_root}/03-sunrise-peak.aiff",
            title="Sunrise Peak",
            artist="Xfin Fixture",
            bpm=126.0,
            camelot_key="9B",
            energy_level=7,
            genre="Melodic House",
            tags=["lift", "peak"],
            metadata_status="complete",
            source_fields={"bpm": "TBPM", "camelot_key": "TKEY", "energy_level": "COMM:Songs-DB_Custom1"},
            raw_metadata={"fixture": "release-smoke"},
        ),
    ]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
