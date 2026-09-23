#!/usr/bin/env python3
"""Aggregate anchor benchmark for the energy-arc playlist strategies.

Reconstructed replacement for the measurement that the frozen spec SPEC-WU25
prescribed (open task 6.1 of `openspec/changes/arc-subset-sequencing`). That spec
was a local-only file in a clone that no longer exists, so the anchor set it
defined is unrecoverable. This tool defines its own anchor set, deterministically
and in the open, so the measurement can be repeated by anyone.

What it measures: for each anchor and each energy-arc strategy, how long the
recommended set actually is, and whether it reaches the requested length. The
defect under test is that arc strategies collapse -- on a raw library input they
were recorded producing sets of about 3 to 5 tracks when 12 were asked for.

Two pool conditions, because the desktop app masks the defect:

  raw       every complete track in the library (what a caller can hand in)
  desktop   the real UI path: `plan_recommendation_candidates` with
            `pool_size_for_slot` for a 30-minute slot, which caps at 120

Never point this at the live application database. Pass a scratch copy:

    sqlite3 ~/.xfinaudio/xfinaudio.sqlite3 ".backup /tmp/scratch.sqlite3"
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from xfinaudio.application.recommendation_candidates import (
    plan_recommendation_candidates,
    pool_size_for_slot,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.track_repository import TrackRepository
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.playlist_service import recommend_playlist

ARC_STRATEGIES = ("harmonic_journey", "warmup", "build", "peak_time")

# Mirrors the desktop call site: a 30-minute slot, 120 seconds played per track.
DESKTOP_SLOT_MINUTES = 30.0
DESKTOP_PLAYED_SECONDS = 120.0


def select_anchors(complete: list[TrackRecord], count: int) -> list[TrackRecord]:
    """Pick `count` anchors evenly spaced across the path-ordered library.

    Deterministic and spread across the whole library rather than clustered at
    the start of the scan order. The spec's own anchor set is lost, so this is a
    documented replacement, not a reproduction of it.
    """
    if count >= len(complete):
        return list(complete)
    step = len(complete) / count
    return [complete[int(index * step)] for index in range(count)]


def build_pool(
    mode: str,
    complete: list[TrackRecord],
    anchor: TrackRecord,
    strategy_name: str,
) -> list[TrackRecord]:
    """Return the candidate pool for one anchor under one pool condition."""
    if mode == "raw":
        return complete
    controls = DJControls(start_path=anchor.path)
    return plan_recommendation_candidates(
        scanned_records=complete,
        controls=controls,
        limit=pool_size_for_slot(
            slot_minutes=DESKTOP_SLOT_MINUTES,
            played_seconds_per_track=DESKTOP_PLAYED_SECONDS,
        ),
        strategy_name=strategy_name,
    )


def run_one(
    mode: str,
    complete: list[TrackRecord],
    anchor: TrackRecord,
    strategy_name: str,
    target_count: int,
) -> tuple[int, int, list[str]]:
    """Return (pool size, resulting set length, warnings) for one cell."""
    pool = build_pool(mode, complete, anchor, strategy_name)
    recommendation = recommend_playlist(
        pool,
        strategy_name,
        controls=DJControls(start_path=anchor.path),
        target_count=target_count,
    )
    return len(pool), len(recommendation.ordered_tracks), list(recommendation.warnings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="scratch copy of the library database")
    parser.add_argument("--anchors", type=int, default=40)
    parser.add_argument("--target-count", type=int, default=12)
    parser.add_argument("--strategies", default=",".join(ARC_STRATEGIES))
    parser.add_argument("--modes", default="raw,desktop")
    parser.add_argument("--limit-anchors", type=int, default=0, help="0 means all; use 1 to time a single anchor")
    parser.add_argument("--json-out", default="")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        print(f"error: database not found: {db_path}", file=sys.stderr)
        return 2
    live = Path.home() / ".xfinaudio" / "xfinaudio.sqlite3"
    if db_path.resolve() == live.resolve():
        print("error: refusing to read the live database; pass a scratch copy", file=sys.stderr)
        return 2

    strategies = [name for name in args.strategies.split(",") if name]
    modes = [mode for mode in args.modes.split(",") if mode]

    repository = TrackRepository(db_path)
    tracks = repository.list_tracks()
    complete = [track for track in tracks if track.metadata_status == "complete"]
    print(f"library: {len(tracks)} tracks, {len(complete)} complete")

    anchors = select_anchors(complete, args.anchors)
    if args.limit_anchors:
        anchors = anchors[: args.limit_anchors]
    print(f"anchors: {len(anchors)} of a requested {args.anchors}\n")

    results: dict[str, dict[str, dict[str, object]]] = {}
    started = time.perf_counter()

    for mode in modes:
        for strategy_name in strategies:
            lengths: list[int] = []
            full = 0
            pool_sizes: list[int] = []
            cell_started = time.perf_counter()
            for anchor in anchors:
                pool_size, length, warnings = run_one(mode, complete, anchor, strategy_name, args.target_count)
                pool_sizes.append(pool_size)
                lengths.append(length)
                if length >= args.target_count:
                    full += 1
                if args.verbose:
                    print(
                        f"  {mode:8s} {strategy_name:18s} pool={pool_size:5d} len={length:3d} warnings={len(warnings)}"
                    )
            elapsed = time.perf_counter() - cell_started
            results.setdefault(mode, {})[strategy_name] = {
                "anchors": len(anchors),
                "target_count": args.target_count,
                "mean_length": round(statistics.fmean(lengths), 4) if lengths else 0.0,
                "median_length": statistics.median(lengths) if lengths else 0,
                "min_length": min(lengths) if lengths else 0,
                "max_length": max(lengths) if lengths else 0,
                "full_sets": full,
                "mean_pool": round(statistics.fmean(pool_sizes), 2) if pool_sizes else 0.0,
                "seconds": round(elapsed, 2),
            }

    total = time.perf_counter() - started
    print(f"\n{'mode':9s} {'strategy':18s} {'mean':>7s} {'median':>7s} {'full':>7s} {'pool':>8s} {'sec':>7s}")
    print("-" * 72)
    for mode in modes:
        for strategy_name in strategies:
            row = results[mode][strategy_name]
            print(
                f"{mode:9s} {strategy_name:18s} {row['mean_length']:>7} {row['median_length']:>7} "
                f"{str(row['full_sets']) + '/' + str(row['anchors']):>7} {row['mean_pool']:>8} {row['seconds']:>7}"
            )
    print(f"\ntotal elapsed: {total:.1f}s")

    if args.json_out:
        payload = {
            "db": str(db_path),
            "library_tracks": len(tracks),
            "library_complete": len(complete),
            "anchors_selected": len(anchors),
            "target_count": args.target_count,
            "results": results,
            "elapsed_seconds": round(total, 2),
        }
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
