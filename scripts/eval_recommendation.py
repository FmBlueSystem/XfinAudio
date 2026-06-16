"""Read-only CLI for the recommendation quality harness.

Loads tracks from the application library (or a given SQLite DB), runs every requested strategy
over deterministically sampled anchors, and prints scorer-independent quality metrics. It never
mutates audio, the library, or any Serato file.

Example:
    uv run python scripts/eval_recommendation.py --sample-size 30 --requested-size 12
"""

from __future__ import annotations

import argparse
from pathlib import Path

from xfinaudio.library.track_repository import TrackRepository
from xfinaudio.recommendation.evaluation import EvalConfig, evaluate_recommendations
from xfinaudio.recommendation.strategies import available_strategies

# Mirror of xfinaudio.desktop.app default; replicated to avoid importing the Qt desktop package.
_DEFAULT_DB_PATH = Path.home() / ".xfinaudio" / "xfinaudio.sqlite3"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate recommendation quality (read-only).")
    parser.add_argument("--db", type=Path, default=_DEFAULT_DB_PATH, help="Path to the track SQLite database.")
    parser.add_argument("--seed", type=int, default=1234, help="Deterministic anchor-sampling seed.")
    parser.add_argument("--sample-size", type=int, default=30, help="Number of anchor tracks to sample.")
    parser.add_argument("--requested-size", type=int, default=12, help="Target playlist length for the fill metric.")
    parser.add_argument("--candidate-limit", type=int, default=25, help="Candidate pool size (desktop default 25).")
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=list(available_strategies()),
        help="Strategy names to evaluate (default: all).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    tracks = TrackRepository(args.db).list_tracks()
    config = EvalConfig(
        seed=args.seed,
        sample_size=args.sample_size,
        requested_size=args.requested_size,
        candidate_limit=args.candidate_limit,
        strategies=tuple(args.strategies),
    )
    report = evaluate_recommendations(tracks, config)
    print(report.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
