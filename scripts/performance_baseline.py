#!/usr/bin/env python3
"""Performance baseline reporter for core XfinAudio workflows.

Runs deterministic, audio-free scenarios and prints a Markdown table.
Exits with a non-zero status if any scenario exceeds its threshold.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Allow running the script directly from the project root without installing.
src_root = Path(__file__).resolve().parent.parent / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from xfinaudio.exporting.playlist_exporters import (  # noqa: E402
    default_exporter_registry,
    export_quality_report_json,
)
from xfinaudio.library.models import TrackRecord  # noqa: E402
from xfinaudio.quality.dj_readiness import build_dj_readiness_report  # noqa: E402
from xfinaudio.quality.recommendation_quality import build_quality_report  # noqa: E402
from xfinaudio.recommendation.playlist_service import recommend_playlist  # noqa: E402

_CAMELOT_KEYS = ["8A", "8B", "9A", "9B", "10A", "10B", "11A", "11B", "12A", "12B"]
_BPMS = [120.0, 122.0, 124.0, 125.0, 126.0, 128.0, 130.0, 132.0]


SCENARIOS = {
    "recommend_playlist_50": 2.0,
    "recommend_playlist_100": 4.0,
    "export_playlist_100": 1.0,
    "quality_report_100": 1.0,
    "dj_readiness_100": 1.0,
}


def _make_complete_tracks(count: int) -> list[TrackRecord]:
    """Generate deterministic complete TrackRecords for benchmarking."""
    tracks: list[TrackRecord] = []
    for i in range(count):
        key = _CAMELOT_KEYS[i % len(_CAMELOT_KEYS)]
        bpm = _BPMS[i % len(_BPMS)]
        energy = (i % 10) + 1
        tracks.append(
            TrackRecord(
                path=f"/music/perf/track_{i:05d}.mp3",
                title=f"Perf Track {i}",
                artist=f"Artist {i % 50}",
                bpm=bpm,
                camelot_key=key,
                energy_level=energy,
                duration=240.0,
                genre="House",
                tags=["house", "electronic"],
                metadata_status="complete",
                source_fields={"TBPM": str(bpm), "TKEY": key},
            )
        )
    return tracks


def _run_scenarios() -> list[dict[str, object]]:
    """Execute all baseline scenarios and return result rows."""
    registry = default_exporter_registry()
    results: list[dict[str, object]] = []

    for count in (50, 100):
        tracks = _make_complete_tracks(count)
        start = time.perf_counter()
        recommendation = recommend_playlist(tracks, strategy_name="harmonic_journey")
        elapsed = time.perf_counter() - start
        results.append(
            {
                "operation": f"recommend_playlist({count})",
                "tracks": len(recommendation.ordered_tracks),
                "elapsed": elapsed,
                "threshold": SCENARIOS[f"recommend_playlist_{count}"],
            }
        )

    tracks_100 = _make_complete_tracks(100)
    recommendation_100 = recommend_playlist(tracks_100, strategy_name="harmonic_journey")

    start = time.perf_counter()
    for fmt in ("json", "csv", "m3u"):
        registry.export(fmt, recommendation_100)
    elapsed = time.perf_counter() - start
    results.append(
        {
            "operation": "export json/csv/m3u",
            "tracks": len(recommendation_100.ordered_tracks),
            "elapsed": elapsed,
            "threshold": SCENARIOS["export_playlist_100"],
        }
    )

    quality_report = build_quality_report(recommendation_100)
    start = time.perf_counter()
    export_quality_report_json(quality_report)
    elapsed = time.perf_counter() - start
    results.append(
        {
            "operation": "quality report json",
            "tracks": len(recommendation_100.ordered_tracks),
            "elapsed": elapsed,
            "threshold": SCENARIOS["quality_report_100"],
        }
    )

    start = time.perf_counter()
    build_dj_readiness_report(recommendation_100, quality_report)
    elapsed = time.perf_counter() - start
    results.append(
        {
            "operation": "dj readiness report",
            "tracks": len(recommendation_100.ordered_tracks),
            "elapsed": elapsed,
            "threshold": SCENARIOS["dj_readiness_100"],
        }
    )

    return results


def main(argv: list[str] | None = None) -> int:
    """Run performance baselines and print a Markdown report."""
    results = _run_scenarios()

    print("# XfinAudio Performance Baseline\n")
    print("| Operation | Tracks | Elapsed (s) | Threshold (s) | Status |")
    print("|-----------|--------|-------------|---------------|--------|")
    failed = False
    for row in results:
        status = "pass" if row["elapsed"] < row["threshold"] else "fail"
        if status == "fail":
            failed = True
        print(f"| {row['operation']} | {row['tracks']} | {row['elapsed']:.4f} | {row['threshold']} | {status} |")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
