#!/usr/bin/env python3
"""Runtime memory probe for the XfinAudio desktop app.

Drives the real app offscreen against a scratch copy of a library DB, runs a
folder scan, and reports memory growth plus render-storm counters.

Answers two questions the Activity Monitor cannot:
  1. Is the reported multi-GB number resident memory (a real leak) or just
     reserved virtual address space (benign for Qt)? Both are reported.
  2. How many full UI re-renders does one scan actually trigger?

Usage:
    .venv/bin/python scripts/perf_probe.py --folder /path/to/music
    .venv/bin/python scripts/perf_probe.py --folder /path/to/music --tab 5

Baseline/after comparison: run once before a fix and once after, with the same
--folder and --tab, then diff the two Markdown tables.
"""

from __future__ import annotations

import argparse
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any

# Offscreen must be set before any Qt import.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Allow running the script directly from the project root without installing.
src_root = Path(__file__).resolve().parent.parent / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

_SAMPLE_INTERVAL_SECONDS = 0.5
_TAB_NAMES = {0: "Library", 1: "Build", 2: "Review", 3: "Export", 5: "Metadata"}


class Counters:
    """Mutable tally of instrumented UI operations."""

    def __init__(self) -> None:
        self.sync_state = 0
        self.render_screens = 0
        self.library_populate = 0
        self.library_rows = 0
        self.metadata_populate = 0
        self.metadata_rows = 0


def _current_memory_mb() -> tuple[float, float]:
    """Return (resident, virtual) memory of this process in MB via ps(1).

    ponytail: shelling out to ps instead of adding a psutil dependency for a
    diagnostic script. Swap to psutil.memory_full_info() if USS/footprint is
    ever needed.
    """
    output = subprocess.run(
        ["ps", "-o", "rss=,vsz=", "-p", str(os.getpid())],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return int(output[0]) / 1024, int(output[1]) / 1024


def _peak_resident_mb() -> float:
    """Return the process peak resident set size in MB.

    macOS reports ru_maxrss in bytes; Linux reports it in kilobytes.
    """
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    return peak / divisor


def _instrument(counters: Counters) -> None:
    """Wrap the hot UI paths with counting decorators."""
    from xfinaudio.desktop import library_screen_rendering
    from xfinaudio.desktop.app_controller import AppController
    from xfinaudio.desktop.screens import metadata_screen

    original_sync = AppController.sync_state
    original_render = AppController.render_screens
    original_library = library_screen_rendering.LibraryScreenRenderingMixin._populate_table
    original_metadata = metadata_screen.MetadataScreen._populate_table

    def counted_sync(self: Any) -> Any:
        counters.sync_state += 1
        return original_sync(self)

    def counted_render(self: Any) -> Any:
        counters.render_screens += 1
        return original_render(self)

    def counted_library(self: Any, rows: Any) -> Any:
        counters.library_populate += 1
        counters.library_rows += len(rows)
        return original_library(self, rows)

    def counted_metadata(self: Any, rows: Any) -> Any:
        counters.metadata_populate += 1
        counters.metadata_rows += len(rows)
        return original_metadata(self, rows)

    AppController.sync_state = counted_sync
    AppController.render_screens = counted_render
    library_screen_rendering.LibraryScreenRenderingMixin._populate_table = counted_library
    metadata_screen.MetadataScreen._populate_table = counted_metadata


def _pump_until(app: Any, predicate: Any, samples: list[tuple[float, float, float]], timeout: float) -> bool:
    """Process Qt events until predicate() is true, sampling memory as it goes.

    Returns whether the predicate was satisfied before the timeout.
    """
    start = time.perf_counter()
    next_sample = 0.0
    while time.perf_counter() - start < timeout:
        app.processEvents()
        elapsed = time.perf_counter() - start
        if elapsed >= next_sample:
            resident, virtual = _current_memory_mb()
            samples.append((elapsed, resident, virtual))
            next_sample = elapsed + _SAMPLE_INTERVAL_SECONDS
        if predicate():
            resident, virtual = _current_memory_mb()
            samples.append((time.perf_counter() - start, resident, virtual))
            return True
    return False


def _print_report(
    counters: Counters,
    samples: list[tuple[float, float, float]],
    baseline_resident: float,
    track_count: int,
    tab_index: int,
    completed: bool,
    snapshot_before: Any,
) -> None:
    """Print the Markdown probe report."""
    final_resident, final_virtual = _current_memory_mb()
    peak_resident = max((resident for _, resident, _ in samples), default=final_resident)
    peak_virtual = max((virtual for _, _, virtual in samples), default=final_virtual)

    print("\n# XfinAudio runtime memory probe\n")
    print(f"- Active tab during scan: **{_TAB_NAMES.get(tab_index, tab_index)}** (index {tab_index})")
    print(f"- Tracks scanned: **{track_count}**")
    print(f"- Scan completed within timeout: **{'yes' if completed else 'NO — timed out'}**\n")

    print("## Memory\n")
    print("| Metric | MB |")
    print("|--------|-----|")
    print(f"| Resident at startup (baseline) | {baseline_resident:.1f} |")
    print(f"| Resident peak during scan | {peak_resident:.1f} |")
    print(f"| Resident at end | {final_resident:.1f} |")
    print(f"| Resident growth (end - baseline) | {final_resident - baseline_resident:.1f} |")
    print(f"| Virtual peak during scan | {peak_virtual:.1f} |")
    print(f"| Virtual at end | {final_virtual:.1f} |")
    print(f"| Process peak RSS (getrusage) | {_peak_resident_mb():.1f} |\n")
    print(
        "> Resident is the real footprint. A large virtual number with a small "
        "resident number is normal for Qt and is NOT a leak.\n"
    )

    print("## Render storm counters\n")
    print("| Operation | Calls | Rows built |")
    print("|-----------|-------|------------|")
    print(f"| `AppController.sync_state` | {counters.sync_state} | — |")
    print(f"| `AppController.render_screens` | {counters.render_screens} | — |")
    print(f"| Library `_populate_table` | {counters.library_populate} | {counters.library_rows} |")
    print(f"| Metadata `_populate_table` | {counters.metadata_populate} | {counters.metadata_rows} |")
    library_items = counters.library_rows * 12
    metadata_items = counters.metadata_rows * 7
    print(f"\nApproximate `QTableWidgetItem` churn: **{library_items + metadata_items:,}** objects.\n")

    print("## Memory samples\n")
    print("| t (s) | Resident MB | Virtual MB |")
    print("|-------|-------------|------------|")
    for elapsed, resident, virtual in samples:
        print(f"| {elapsed:.1f} | {resident:.1f} | {virtual:.1f} |")

    print("\n## Top allocations by line (tracemalloc)\n")
    snapshot_after = tracemalloc.take_snapshot()
    print("| Location | Size delta |")
    print("|----------|------------|")
    for stat in snapshot_after.compare_to(snapshot_before, "lineno")[:15]:
        location = stat.traceback.format()[0].strip() if stat.traceback else "?"
        print(f"| `{location}` | {stat.size_diff / (1024 * 1024):+.1f} MB |")


def main(argv: list[str] | None = None) -> int:
    """Run the probe and print a Markdown report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True, help="Music folder to scan.")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path.home() / ".xfinaudio" / "xfinaudio.sqlite3",
        help="Library DB to copy into a scratch location. Use --fresh for an empty DB.",
    )
    parser.add_argument("--fresh", action="store_true", help="Start from an empty DB instead of copying --db.")
    parser.add_argument(
        "--tab",
        type=int,
        default=5,
        help="Workflow tab index kept active during the scan (5 = Metadata, the worst case).",
    )
    parser.add_argument("--timeout", type=float, default=1800.0, help="Seconds to wait for the scan to finish.")
    args = parser.parse_args(argv)

    if not args.folder.is_dir():
        print(f"error: --folder is not a directory: {args.folder}", file=sys.stderr)
        return 2

    scratch = Path(tempfile.mkdtemp(prefix="xfinaudio-perf-probe-"))
    db_copy = scratch / "library.sqlite3"
    if args.fresh:
        print(f"Starting from an empty DB at {db_copy}")
    elif args.db.is_file():
        print(f"Copying {args.db} ({args.db.stat().st_size / (1024 * 1024):.0f} MB) to {db_copy}")
        shutil.copy2(args.db, db_copy)
    else:
        print(f"warning: {args.db} not found; starting from an empty DB", file=sys.stderr)

    counters = Counters()
    _instrument(counters)

    from PySide6.QtWidgets import QApplication  # noqa: PLC0415

    from xfinaudio.desktop.main_window import MainWindow  # noqa: PLC0415

    tracemalloc.start()
    app = QApplication.instance() or QApplication([])
    window = MainWindow.with_defaults(db_path=db_copy, settings_path=scratch / "settings.json")
    window.show()
    app.processEvents()

    window.workflow_sidebar.setCurrentRow(args.tab)
    app.processEvents()

    baseline_resident, _ = _current_memory_mb()
    snapshot_before = tracemalloc.take_snapshot()
    counters.__init__()  # discard startup renders; measure the scan only

    print(f"Scanning {args.folder} with tab {args.tab} active...")
    samples: list[tuple[float, float, float]] = []

    # Mirror scan_selected_folder() (desktop/scan_service.py:165-171): begin_scan_state()
    # creates the token that _end_scan_state() later clears, which is our done signal.
    scan_service = window._scan_service
    scan_service.begin_scan_state()
    token = scan_service.current_scan_cancellation_token
    scan_service.start_scan(args.folder, token)

    # The scan token clears in _end_scan_state(), but the expensive phase is the
    # spectral pass that on_completed() kicks off right after (library_controller.py:378).
    # That one re-renders with scanned_records already populated, so wait for both.
    completed = _pump_until(
        app,
        lambda: scan_service.current_scan_cancellation_token is None and not window._state.is_completing_spectral,
        samples,
        args.timeout,
    )
    if not completed:
        token.cancel()
        app.processEvents()

    track_count = len(window.scanned_records or [])
    _print_report(counters, samples, baseline_resident, track_count, args.tab, completed, snapshot_before)

    tracemalloc.stop()
    scan_service.cancel()
    window.close()
    app.processEvents()
    shutil.rmtree(scratch, ignore_errors=True)
    return 0 if completed else 1


if __name__ == "__main__":
    sys.exit(main())
