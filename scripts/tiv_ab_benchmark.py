#!/usr/bin/env python3
"""Offline A/B benchmark for audio-derived tonal compatibility (Harmonic core v2).

The Tonal Interval Vector (TIV) component is disabled by default so every
existing transition score stays byte-identical. This tool measures what happens
when it is switched on: it runs a fixed set of intents over a library twice --
the default arm (tonal weight 0.0) and the tonal arm (a non-zero weight applied
through ``ScoringWeights`` ``weights_override``) -- and prints a deterministic
comparison of the two orderings.

What it reports per (intent, anchor): the two orders, the per-transition tonal
components, the positions where the orders diverge, and the two totals. It reads
a library database, so it must never touch the live application database. Pass a
scratch copy:

    sqlite3 ~/.xfinaudio/xfinaudio.sqlite3 ".backup /tmp/scratch.sqlite3"

The two arms run fully in-process; no audio is decoded and nothing is written
back to the database.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from xfinaudio.library.models import TrackRecord
from xfinaudio.library.track_repository import TrackRepository
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation, recommend_playlist
from xfinaudio.recommendation.scoring import ScoringWeights
from xfinaudio.recommendation.strategies import get_strategy

DEFAULT_INTENTS = ("harmonic_journey", "warmup", "build", "peak_time")
DEFAULT_TONAL_WEIGHT = 0.20


@dataclass(frozen=True)
class ArmComparison:
    """Deterministic comparison of the default and tonal arms for one anchor."""

    intent: str
    anchor_path: str
    default_order: tuple[str, ...]
    tonal_order: tuple[str, ...]
    differing_positions: tuple[int, ...]
    default_total: float
    tonal_total: float
    default_tonal_components: tuple[float | None, ...]
    tonal_tonal_components: tuple[float | None, ...]


def arm_weights(intent: str, tonal_weight: float) -> ScoringWeights:
    """Return the strategy weights with only the tonal component overridden."""
    return get_strategy(intent).weights.model_copy(update={"tonal": tonal_weight})


def run_arm(
    tracks: list[TrackRecord],
    intent: str,
    anchor_path: str,
    tonal_weight: float,
    target_count: int,
) -> PlaylistRecommendation:
    """Recommend one arm for one anchor using the intent's weights plus override."""
    return recommend_playlist(
        tracks,
        intent,
        controls=DJControls(start_path=anchor_path),
        weights_override=arm_weights(intent, tonal_weight),
        target_count=target_count,
    )


def tonal_components(recommendation: PlaylistRecommendation) -> list[float | None]:
    """Return the per-transition tonal component (None when not measurable)."""
    return [score.component_scores.get("tonal") for score in recommendation.transition_scores]


def differing_positions(left: Sequence[str], right: Sequence[str]) -> list[int]:
    """Return the indices where two orderings disagree, over the longer length."""
    length = max(len(left), len(right))
    return [
        index
        for index in range(length)
        if (left[index] if index < len(left) else None) != (right[index] if index < len(right) else None)
    ]


def build_comparison(
    intent: str,
    anchor_path: str,
    default: PlaylistRecommendation,
    tonal: PlaylistRecommendation,
) -> ArmComparison:
    """Assemble the deterministic comparison of two arms for one anchor."""
    default_order = tuple(track.path for track in default.ordered_tracks)
    tonal_order = tuple(track.path for track in tonal.ordered_tracks)
    return ArmComparison(
        intent=intent,
        anchor_path=anchor_path,
        default_order=default_order,
        tonal_order=tonal_order,
        differing_positions=tuple(differing_positions(list(default_order), list(tonal_order))),
        default_total=default.total_score,
        tonal_total=tonal.total_score,
        default_tonal_components=tuple(tonal_components(default)),
        tonal_tonal_components=tuple(tonal_components(tonal)),
    )


def select_anchors(complete: list[TrackRecord], count: int) -> list[TrackRecord]:
    """Pick ``count`` anchors evenly spaced across the path-ordered library."""
    if count >= len(complete):
        return list(complete)
    step = len(complete) / count
    return [complete[int(index * step)] for index in range(count)]


def _is_live_database(db_path: Path, live: Path) -> bool:
    """Detect the live database by path and, crucially, by file identity.

    A resolved-path comparison misses a hard link (or bind mount) that reaches
    the same inode from a different path, so the benchmark could read the live
    library through it. ``Path.samefile`` compares ``(st_dev, st_ino)``.
    """
    if db_path.resolve() == live.resolve():
        return True
    try:
        return db_path.samefile(live)
    except OSError:
        return False


def _format_components(components: tuple[float | None, ...]) -> str:
    return "[" + ", ".join("none" if value is None else f"{value:.3f}" for value in components) + "]"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="scratch copy of the library database")
    parser.add_argument("--anchors", type=int, default=40)
    parser.add_argument("--target-count", type=int, default=12)
    parser.add_argument("--tonal-weight", type=float, default=DEFAULT_TONAL_WEIGHT)
    parser.add_argument("--intents", default=",".join(DEFAULT_INTENTS))
    parser.add_argument("--json-out", default="")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        print(f"error: database not found: {db_path}", file=sys.stderr)
        return 2
    live = Path.home() / ".xfinaudio" / "xfinaudio.sqlite3"
    if _is_live_database(db_path, live):
        print("error: refusing to read the live database; pass a scratch copy", file=sys.stderr)
        return 2

    intents = [name for name in args.intents.split(",") if name]

    repository = TrackRepository(db_path)
    tracks = repository.list_tracks()
    complete = [track for track in tracks if track.metadata_status == "complete"]
    print(f"library: {len(tracks)} tracks, {len(complete)} complete")

    anchors = select_anchors(complete, args.anchors)
    print(f"anchors: {len(anchors)} of a requested {args.anchors}")
    print(f"tonal arm weight: {args.tonal_weight:g}\n")

    comparisons: list[ArmComparison] = []
    for intent in intents:
        changed = 0
        for anchor in anchors:
            default = run_arm(complete, intent, anchor.path, 0.0, args.target_count)
            tonal = run_arm(complete, intent, anchor.path, args.tonal_weight, args.target_count)
            comparison = build_comparison(intent, anchor.path, default, tonal)
            comparisons.append(comparison)
            if comparison.differing_positions:
                changed += 1
            if args.verbose:
                print(
                    f"  {intent:18s} {Path(anchor.path).name:24s} "
                    f"default={comparison.default_total:.4f} tonal={comparison.tonal_total:.4f} "
                    f"differing={list(comparison.differing_positions)}"
                )
        print(f"{intent:18s} anchors={len(anchors):3d} changed_orders={changed}")

    print(f"\n{'intent':18s} {'differing':>10s} {'default_total':>14s} {'tonal_total':>12s}")
    print("-" * 58)
    for intent in intents:
        rows = [comparison for comparison in comparisons if comparison.intent == intent]
        if not rows:
            continue
        differing = sum(len(row.differing_positions) for row in rows)
        default_total = sum(row.default_total for row in rows) / len(rows)
        tonal_total = sum(row.tonal_total for row in rows) / len(rows)
        print(f"{intent:18s} {differing:>10d} {default_total:>14.4f} {tonal_total:>12.4f}")

    if args.verbose:
        print("\nper-transition tonal components (default arm / tonal arm)")
        for comparison in comparisons:
            print(f"  {comparison.intent:18s} {Path(comparison.anchor_path).name:24s}")
            print(f"    default: {_format_components(comparison.default_tonal_components)}")
            print(f"    tonal:   {_format_components(comparison.tonal_tonal_components)}")

    if args.json_out:
        payload = {
            "db": str(db_path),
            "library_tracks": len(tracks),
            "library_complete": len(complete),
            "anchors_selected": len(anchors),
            "tonal_weight": args.tonal_weight,
            "target_count": args.target_count,
            "comparisons": [
                {
                    "intent": comparison.intent,
                    "anchor_path": comparison.anchor_path,
                    "differing_positions": list(comparison.differing_positions),
                    "default_total": round(comparison.default_total, 6),
                    "tonal_total": round(comparison.tonal_total, 6),
                    "default_tonal_components": list(comparison.default_tonal_components),
                    "tonal_tonal_components": list(comparison.tonal_tonal_components),
                    "default_order": list(comparison.default_order),
                    "tonal_order": list(comparison.tonal_order),
                }
                for comparison in comparisons
            ],
        }
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
