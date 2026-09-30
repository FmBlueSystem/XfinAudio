#!/usr/bin/env python3
"""Replay synthetic cached profiles through Qt; no audio, database, or network IO.

Run with QT_QPA_PLATFORM=offscreen and PYTHONPATH=src. Table construction is
excluded from timings. Elapsed time is informational; deterministic counters
show publication/copy/lookup work. Use --max-results for bounded baselines.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from types import SimpleNamespace

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QWidget

from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_columns import COLUMNS, column_index
from xfinaudio.desktop.library_controller import LibraryController
from xfinaudio.library.models import TrackRecord


def measure(app: QApplication, size: int, max_results: int | None) -> dict[str, object]:
    records = [TrackRecord(path=f"/synthetic/{i:06d}.flac", title=f"Track {i}") for i in range(size)]
    state = AppState().with_scanned_records(records)
    parent = QWidget()
    table = QTableWidget(size, len(COLUMNS), parent)
    path_column, color_column = column_index("Path"), column_index("Color")
    for row, record in enumerate(records):
        table.setItem(row, path_column, QTableWidgetItem(record.path))
        table.setItem(row, color_column, QTableWidgetItem(""))
    counts = {"publications": 0, "collection_replacements": 0, "path_item_reads": 0, "sync_requests": 0}
    previous = state

    def publish(updated: AppState) -> None:
        nonlocal previous
        counts["publications"] += 1
        counts["collection_replacements"] += int(updated.scanned_records is not previous.scanned_records)
        counts["collection_replacements"] += int(updated.records_by_path is not previous.records_by_path)
        previous = updated

    original_item = table.item

    def counted_item(row: int, column: int) -> QTableWidgetItem | None:
        if column == path_column:
            counts["path_item_reads"] += 1
        return original_item(row, column)

    table.item = counted_item

    def request_sync() -> None:
        counts["sync_requests"] += 1

    controller = LibraryController(
        state=state,
        workflow_service=None,
        widgets=SimpleNamespace(
            library_screen=SimpleNamespace(tracks_table=table, set_loudness_details=lambda *args, **kwargs: None)
        ),
        access=SimpleNamespace(state_setter=publish, selected_paths=[]),
        audio_player=None,
        sync_state=lambda: None,
        request_sync=request_sync,
        tr=lambda text: text,
        log=logging.getLogger("benchmark"),
        parent=parent,
    )
    count = min(size, max_results or size)
    selected = [records[i * (size - 1) // max(1, count - 1)] for i in range(count)]
    selected_paths = {record.path for record in selected}
    profile = SpectralProfile(red_ratio=1, green_ratio=0, blue_ratio=0, dominant_color="RED")
    next_row = chunks = 0
    heartbeat_gaps: list[float] = []
    last_heartbeat = time.perf_counter()
    heartbeat = QTimer(parent)

    def beat() -> None:
        nonlocal last_heartbeat
        now = time.perf_counter()
        heartbeat_gaps.append(now - last_heartbeat)
        last_heartbeat = now

    heartbeat.timeout.connect(beat)
    heartbeat.start(1)

    def pump() -> None:
        nonlocal next_row, chunks
        stop = min(count, next_row + 128)
        for i in range(next_row, stop):
            controller.on_spectral_profile_ready(selected[i].path, profile)
        next_row = stop
        chunks += 1
        if next_row < count:
            QTimer.singleShot(0, pump)
        else:
            QTimer.singleShot(5, app.quit)  # Drain the last batch and heartbeat.

    begin = time.perf_counter()
    QTimer.singleShot(0, pump)
    app.exec()
    elapsed = time.perf_counter() - begin
    heartbeat.stop()
    current = controller._state
    assert all(
        record.spectral_profile == (profile if record.path in selected_paths else None)
        for record in current.scanned_records
    )
    assert all(current.records_by_path[record.path].spectral_profile == profile for record in selected)
    assert all(record.spectral_profile is None for record in records)
    assert all(
        bool(original_item(i, color_column).text()) == (record.path in selected_paths)
        for i, record in enumerate(records)
    )
    result = dict(
        size=size,
        cached_results=count,
        chunk_size=128,
        chunks=chunks,
        elapsed_s=round(elapsed, 6),
        **counts,
        heartbeat_events=len(heartbeat_gaps),
        heartbeat_max_gap_s=round(max(heartbeat_gaps, default=0), 6),
        state_equivalent=True,
        old_snapshot_unchanged=True,
        all_expected_cells_painted=True,
        full_replay=count == size,
    )
    controller.shutdown()
    parent.deleteLater()
    app.processEvents()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[1000, 10000, 50000])
    parser.add_argument("--max-results", type=int)
    args = parser.parse_args()
    if any(size <= 0 for size in args.sizes) or (args.max_results is not None and args.max_results <= 0):
        parser.error("sizes and max-results must be positive")
    app = QApplication([])
    for size in args.sizes:
        print(json.dumps(measure(app, size, args.max_results)), flush=True)


if __name__ == "__main__":
    main()
