"""Synthetic, Qt-free parity for local Library and saved-set operations."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.library_browse import LibraryBrowser
from xfinaudio.headless.saved_browser import SavedBrowser
from xfinaudio.library.models import TrackRecord


@pytest.fixture
def browser(tmp_path: Path):
    backend = HeadlessBackend(tmp_path / "data")
    root = tmp_path / "music"
    root.mkdir()
    backend.roots = [root]
    (backend.data_dir / "roots.json").write_text(json.dumps([str(root)]))
    rows = [
        TrackRecord(
            path=str(root / "a.flac"),
            title="Alpha",
            artist="DJ",
            genre="House",
            bpm=120,
            camelot_key="8A",
            energy_level=4,
            duration=120,
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(root / "b.flac"),
            title="Alpha (v2)",
            artist="DJ",
            genre="House",
            bpm=121,
            camelot_key="8A",
            energy_level=5,
            duration=180,
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(root / "c.flac"),
            title="Beta",
            artist="DJ",
            genre="Techno",
            bpm=130,
            camelot_key="9A",
            energy_level=7,
            duration=240,
            metadata_status="complete",
        ),
        TrackRecord(
            path=str(root / "d.flac"),
            title="Unknown",
            artist="",
            genre="House",
            metadata_status="incomplete",
            missing_required_fields=["bpm", "camelot_key", "energy_level"],
        ),
    ]
    backend.repository.save_scan_results(rows)
    return backend, LibraryBrowser(backend), SavedBrowser(backend), rows


def test_interpreted_and_manual_queries_reuse_original_filters(browser):
    backend, library, _, _ = browser
    result = library.execute("library.query", {"request": "House BPM 120-125 key 8A energy 4-5"})
    assert [t["title"] for t in result["tracks"]] == ["Alpha", "Alpha (v2)"]
    assert result["query"]["bpm_min"] == 120
    assert result["genres"] == ["House", "Techno"]
    manual = library.execute("library.query", {"query": {"genre": "House", "energy_min": 5}})
    assert [t["title"] for t in manual["tracks"]] == ["Alpha (v2)"]
    assert str(backend.data_dir.parent) not in json.dumps(result)
    for params in (
        {"request": "play me a mood"},
        {"query": {"bpm_min": 140, "bpm_max": 120}},
        {"query": {"energy_min": 0}},
        {"query": {"path": "/private"}},
        {"query": {}, "request": "House"},
        {"hideDuplicates": "yes"},
        {"sortBy": "path"},
    ):
        with pytest.raises(BackendError):
            library.execute("library.query", params)


def test_original_duplicate_representation_and_numeric_sort_are_display_only(browser):
    backend, library, _, rows = browser
    result = library.execute("library.query", {"hideDuplicates": True, "sortBy": "bpm", "descending": True})
    assert [t["title"] for t in result["tracks"]] == ["Beta", "Alpha", "Unknown"]
    assert result["suppressedCount"] == 1
    assert len(backend.repository.list_tracks()) == len(rows)
    incomplete = library.execute("library.query", {"status": "incomplete"})
    assert [t["title"] for t in incomplete["tracks"]] == ["Unknown"]


def test_local_search_and_comparison_use_actual_saved_evidence(browser):
    backend, _, saved, rows = browser
    first = backend.playlists.create("Warmup", [rows[0].path, rows[1].path])
    second = backend.playlists.create("Main", [rows[1].path, rows[2].path])
    result = saved.execute("playlist.search", {"request": "House under 3 tracks"})
    assert {p["id"] for p in result["playlists"]} == {first.id, second.id}
    comparison = saved.execute("playlist.compare", {"playlistIds": [first.id, second.id]})
    assert "1 shared unique track" in comparison["comparison"]
    assert "energy 4.5 (2/2 known)" in comparison["comparison"]
    assert str(backend.data_dir.parent) not in json.dumps([result, comparison])
    for ids in ([first.id], [first.id, first.id], [first.id, 999], [True, second.id]):
        with pytest.raises(BackendError):
            saved.execute("playlist.compare", {"playlistIds": ids})


def test_deletion_requires_confirmation_exact_revision_and_one_use_preview(browser):
    backend, _, saved, rows = browser
    original = backend.playlists.create("Keep", [r.path for r in rows])
    preview = saved.execute("playlist.delete.preview", {"playlistId": original.id})
    assert preview["name"] == "Keep" and preview["trackCount"] == 4
    assert len(preview["revision"]) == 64
    with pytest.raises(BackendError):
        saved.execute("playlist.delete.commit", {"previewId": preview["previewId"], "confirmed": False})
    assert backend.playlists.get_by_id(original.id) == original
    backend.playlists.update_name(original.id, "Changed")
    with pytest.raises(BackendError, match="changed"):
        saved.execute("playlist.delete.commit", {"previewId": preview["previewId"], "confirmed": True})
    assert backend.playlists.get_by_id(original.id).name == "Changed"
    assert saved.execute("playlist.deleted.list", {})["playlists"] == []


def test_atomic_archive_survives_restart_restores_original_order_once(browser):
    backend, _, saved, rows = browser
    original = backend.playlists.create(
        "Recover <b>me</b>", [rows[2].path, rows[0].path, rows[2].path, "/missing/audio.flac"]
    )
    preview = saved.execute("playlist.delete.preview", {"playlistId": original.id})
    receipt = saved.execute("playlist.delete.commit", {"previewId": preview["previewId"], "confirmed": True})
    assert backend.playlists.get_by_id(original.id) is None
    with pytest.raises(BackendError):
        saved.execute("playlist.delete.commit", {"previewId": preview["previewId"], "confirmed": True})
    reopened = HeadlessBackend(backend.data_dir)
    recovery = SavedBrowser(reopened)
    listing = recovery.execute("playlist.deleted.list", {})
    assert listing["playlists"][0]["deletionId"] == receipt["deletionId"]
    assert "/missing/" not in json.dumps(listing)
    result = recovery.execute("playlist.restore", {"deletionId": receipt["deletionId"]})
    restored = reopened.playlists.get_by_id(result["id"])
    assert restored.name == original.name and restored.track_paths == original.track_paths
    with pytest.raises(BackendError):
        recovery.execute("playlist.restore", {"deletionId": receipt["deletionId"]})
    assert recovery.execute("playlist.deleted.list", {})["playlists"] == []
    assert len(reopened.playlists.list_summaries()) == 1


def test_archival_failure_rolls_back_active_playlist(browser):
    backend, _, saved, rows = browser
    original = backend.playlists.create("Safe", [rows[0].path])
    preview = saved.execute("playlist.delete.preview", {"playlistId": original.id})
    with sqlite3.connect(backend.playlists.db_path) as db:
        db.execute(
            "CREATE TRIGGER block_archive BEFORE INSERT ON deleted_playlists BEGIN SELECT RAISE(ABORT, 'blocked'); END"
        )
    with pytest.raises(BackendError):
        saved.execute("playlist.delete.commit", {"previewId": preview["previewId"], "confirmed": True})
    assert backend.playlists.get_by_id(original.id) == original


def test_duplicate_hiding_only_suppresses_matches_not_filtered_out_representatives(browser):
    _, library, _, _ = browser
    result = library.execute("library.query", {"query": {"bpm_min": 121}, "hideDuplicates": True})
    assert [t["title"] for t in result["tracks"]] == ["Alpha (v2)", "Beta"]
    assert result["suppressedCount"] == 0
