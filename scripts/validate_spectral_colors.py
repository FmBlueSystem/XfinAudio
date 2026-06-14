"""Validate spectral color classification against a real Mixed In Key library."""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections import Counter
from pathlib import Path

from xfinaudio.audio.spectral_profile import format_spectral_color
from xfinaudio.library.scan_service import MetadataScanService, ScanProgress


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate spectral colors on a real library.")
    parser.add_argument("folder", type=Path, help="Root folder to scan")
    parser.add_argument("--output-csv", type=Path, default=Path("spectral-validation.csv"))
    parser.add_argument("--output-json", type=Path, default=Path("spectral-validation.json"))
    parser.add_argument("--max-workers", type=int, default=None)
    args = parser.parse_args(argv)

    folder = args.folder.resolve()
    service = MetadataScanService()

    progress_counter = {"done": 0, "total": 0}

    def on_progress(progress: ScanProgress) -> None:
        progress_counter["done"] = progress.processed_count
        progress_counter["total"] = progress.total_count
        if progress.processed_count % 100 == 0 or progress.processed_count == progress.total_count:
            print(f"Progress: {progress.processed_count}/{progress.total_count} - {progress.current_path.name}")

    print(f"Scanning {folder} ...")
    start = time.perf_counter()
    records = service.scan(
        folder,
        on_progress=on_progress,
        parallel_spectral_analysis=True,
        spectral_max_workers=args.max_workers,
    )
    elapsed = time.perf_counter() - start
    print(f"Scanned {len(records)} tracks in {elapsed:.1f}s ({len(records) / elapsed:.1f} tracks/s)")

    rows: list[dict[str, str | float | None]] = []
    color_counts: Counter[str] = Counter()
    for record in records:
        color = format_spectral_color(record.spectral_profile, emoji_only=True)
        color_text = record.spectral_profile.dominant_color if record.spectral_profile else "NONE"
        color_counts[color_text] += 1
        rows.append(
            {
                "path": record.path,
                "title": record.title,
                "artist": record.artist,
                "bpm": record.bpm,
                "key": record.camelot_key,
                "energy": record.energy_level,
                "color_emoji": color,
                "color": color_text,
                "red_ratio": record.spectral_profile.red_ratio if record.spectral_profile else None,
                "green_ratio": record.spectral_profile.green_ratio if record.spectral_profile else None,
                "blue_ratio": record.spectral_profile.blue_ratio if record.spectral_profile else None,
            }
        )

    args.output_csv.write_text("", encoding="utf-8")
    with args.output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    args.output_json.write_text(
        json.dumps(
            {
                "folder": str(folder),
                "total_tracks": len(records),
                "elapsed_seconds": elapsed,
                "throughput": len(records) / elapsed if elapsed else 0,
                "color_distribution": dict(color_counts),
                "tracks": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nColor distribution: {dict(color_counts)}")
    print(f"CSV: {args.output_csv}")
    print(f"JSON: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
