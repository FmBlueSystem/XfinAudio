"""Tests for WindowState — domain state container for the desktop session."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.desktop.window_state import WindowState
from xfinaudio.library.models import TrackRecord


def _record(path: str) -> TrackRecord:
    return TrackRecord(path=path, metadata_status="complete")


def test_initial_state_has_sane_defaults():
    state = WindowState()
    assert state.selected_folder is None
    assert state.active_search_query == ""
    assert state.scanned_records == []
    assert state.last_recommendation is None
    assert state.export_history == []


def test_update_folder_returns_new_state():
    state = WindowState()
    updated = state.update_folder(Path("/music"))
    assert updated.selected_folder == Path("/music")
    assert state.selected_folder is None  # original unchanged


def test_update_search_query_returns_new_state():
    state = WindowState()
    updated = state.update_search_query("techno")
    assert updated.active_search_query == "techno"
    assert state.active_search_query == ""


def test_update_scan_stores_records():
    records = [_record("/a.mp3"), _record("/b.mp3")]
    state = WindowState().update_scan(records)
    assert state.scanned_records == records


def test_update_scan_replaces_previous_records():
    first = [_record("/a.mp3")]
    second = [_record("/b.mp3")]
    state = WindowState().update_scan(first).update_scan(second)
    assert state.scanned_records == second


def test_clear_scan_resets_records():
    state = WindowState().update_scan([_record("/a.mp3")]).clear_scan()
    assert state.scanned_records == []


def test_add_export_entry_prepends():
    state = WindowState()
    entry = {"path": "/out/a.crate", "time": "10:00"}
    updated = state.add_export_entry(entry)
    assert updated.export_history[0] == entry


def test_add_export_entry_truncates_to_five():
    state = WindowState()
    for i in range(6):
        state = state.add_export_entry({"path": str(i)})
    assert len(state.export_history) == 5
    assert state.export_history[0]["path"] == "5"


def test_immutability_original_not_mutated():
    original = WindowState()
    original.update_folder(Path("/x"))
    original.update_scan([_record("/a.mp3")])
    assert original.selected_folder is None
    assert original.scanned_records == []
