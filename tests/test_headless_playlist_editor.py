"""Saved-set drafts reuse domain editing without Qt, private paths, or implicit saves."""

from __future__ import annotations

import hashlib
import io
import json
import threading
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from tests.test_headless_backend import tagged_flac
from tests.test_headless_protocol import messages, request
from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.headless.server import JsonlServer


@pytest.fixture
def saved_set(tmp_path: Path):
    root = tmp_path / "music"
    for index in range(3):
        tagged_flac(root / f"{index}.flac", index)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    paths = [str(root / f"{index}.flac") for index in range(3)]
    playlist = backend.playlists.create("Saved set", paths)
    return backend, playlist, root


def ids(snapshot: dict) -> list[str]:
    return [track["id"] for track in snapshot["tracks"]]


def test_open_save_discard_are_explicit_and_rotate_edit_identity(saved_set) -> None:
    backend, original, root = saved_set
    before = {path: hashlib.sha256(path.read_bytes()).digest() for path in root.iterdir()}
    opened = backend.execute("playlist.edit.open", {"playlistId": original.id})
    assert str(UUID(opened["editId"])) == opened["editId"]
    assert opened["playlistId"] == opened["id"] == original.id
    assert len(opened["revision"]) == 64
    assert all(track["missing"] is False for track in opened["tracks"])
    assert str(root) not in json.dumps(opened)
    assert backend.playlists.get_by_id(original.id) == original
    saved = backend.execute(
        "playlist.edit.save", {"editId": opened["editId"], "name": "New name", "trackIds": ids(opened)[::-1][:2]}
    )
    assert saved["editId"] != opened["editId"]
    assert saved["revision"] != opened["revision"]
    assert ids(saved) == ids(opened)[::-1][:2]
    persisted = backend.playlists.get_by_id(original.id)
    assert persisted.name == "New name"
    assert persisted.track_paths == original.track_paths[::-1][:2]
    discarded = backend.execute("playlist.edit.discard", {"editId": saved["editId"]})
    assert ids(discarded) == ids(saved)
    assert discarded["editId"] != saved["editId"]
    assert discarded["revision"] == saved["revision"]
    with pytest.raises(BackendError) as error:
        backend.execute("playlist.edit.save", {"editId": opened["editId"], "name": "Stale", "trackIds": ids(opened)})
    assert error.value.code == "stale_edit"
    assert all(hashlib.sha256(path.read_bytes()).digest() == digest for path, digest in before.items())


def test_missing_entries_remain_explicit_and_survive_save(saved_set) -> None:
    backend, original, root = saved_set
    (root / "1.flac").unlink()
    original = backend.playlists.create("Missing", original.track_paths + [str(root / "unscanned.flac")])
    opened = backend.execute("playlist.edit.open", {"playlistId": original.id})
    assert len(opened["tracks"]) == 4
    assert opened["missingTrackCount"] == 2
    assert [track["missing"] for track in opened["tracks"]] == [False, True, False, True]
    assert opened["tracks"][-1]["status"] == "incomplete"
    assert str(root) not in json.dumps(opened)
    result = backend.execute(
        "playlist.edit.save", {"editId": opened["editId"], "name": "Kept missing", "trackIds": ids(opened)[::-1]}
    )
    assert result["missingTrackCount"] == 2
    assert backend.playlists.get_by_id(original.id).track_paths == original.track_paths[::-1]


def test_source_duplicates_preserved_but_added_or_unknown_refs_rejected(saved_set) -> None:
    backend, original, _ = saved_set
    duplicate = backend.playlists.create("Existing repeats", original.track_paths + original.track_paths[:1])
    opened = backend.execute("playlist.edit.open", {"playlistId": duplicate.id})
    for order in (ids(opened) + ids(opened)[:1], ["0" * 64], [ids(opened)[0]] * 501):
        with pytest.raises(BackendError):
            backend.execute("playlist.edit.save", {"editId": opened["editId"], "name": "No", "trackIds": order})
    assert backend.playlists.get_by_id(duplicate.id) == duplicate
    backend.execute(
        "playlist.edit.save", {"editId": opened["editId"], "name": "Retained", "trackIds": ids(opened)[::-1]}
    )
    assert backend.playlists.get_by_id(duplicate.id).track_paths == duplicate.track_paths[::-1]


def test_offline_preview_uses_real_assessment_without_persisting(saved_set) -> None:
    backend, original, root = saved_set
    opened = backend.execute("playlist.edit.open", {"playlistId": original.id})
    preview = backend.execute(
        "playlist.edit.preview",
        {"editId": opened["editId"], "trackIds": ids(opened)[::-1], "request": "shorten to 2 tracks"},
    )
    assert str(UUID(preview["previewId"])) == preview["previewId"]
    assert preview["editId"] == opened["editId"]
    assert preview["revision"] == opened["revision"]
    assert ids(preview) == ids(opened)[::-1][:2]
    assert "Engine validation (build strategy)" in preview["assessment"]["description"]
    assert isinstance(preview["assessment"]["qualityScore"], float)
    assert preview["assessment"]["readiness"] in {"ready", "needs_review"}
    assert isinstance(preview["assessment"]["warnings"], list)
    assert str(root) not in json.dumps(preview)
    assert backend.playlists.get_by_id(original.id) == original


def test_preview_metadata_gate_does_not_restrict_manual_edits(saved_set) -> None:
    backend, original, root = saved_set
    original = backend.playlists.create("Missing metadata", original.track_paths + [str(root / "unscanned.flac")])
    opened = backend.execute("playlist.edit.open", {"playlistId": original.id})
    with pytest.raises(BackendError) as error:
        backend.execute(
            "playlist.edit.preview", {"editId": opened["editId"], "trackIds": ids(opened), "request": "raise energy"}
        )
    assert error.value.code == "invalid_edit"
    backend.execute("playlist.edit.save", {"editId": opened["editId"], "name": "Manual", "trackIds": ids(opened)[::-1]})
    assert backend.playlists.get_by_id(original.id).track_paths == original.track_paths[::-1]


def test_manual_empty_set_is_allowed(saved_set) -> None:
    backend, original, _ = saved_set
    opened = backend.execute("playlist.edit.open", {"playlistId": original.id})
    saved = backend.execute("playlist.edit.save", {"editId": opened["editId"], "name": "Empty", "trackIds": []})
    assert saved["tracks"] == []


def test_stale_persisted_revision_rejects_save_preview_and_discard_reads_actual(saved_set) -> None:
    backend, original, _ = saved_set
    opened = backend.execute("playlist.edit.open", {"playlistId": original.id})
    backend.playlists.update_name(original.id, "External rename")
    for method, fields in (
        ("playlist.edit.save", {"name": "Overwrite", "trackIds": ids(opened)[::-1]}),
        ("playlist.edit.preview", {"request": "raise energy", "trackIds": ids(opened)}),
    ):
        with pytest.raises(BackendError) as error:
            backend.execute(method, {"editId": opened["editId"], **fields})
        assert error.value.code == "stale_edit"
    discarded = backend.execute("playlist.edit.discard", {"editId": opened["editId"]})
    assert discarded["name"] == "External rename"
    assert ids(discarded) == ids(opened)
    assert discarded["revision"] != opened["revision"]


def test_new_session_and_scan_invalidate_old_edit_context(saved_set) -> None:
    backend, original, root = saved_set
    old = backend.execute("playlist.edit.open", {"playlistId": original.id})
    current = backend.execute("playlist.edit.open", {"playlistId": original.id})
    with pytest.raises(BackendError) as error:
        backend.execute("playlist.edit.discard", {"editId": old["editId"]})
    assert error.value.code == "stale_edit"
    backend.execute("library.scan", {"root": str(root)})
    with pytest.raises(BackendError) as error:
        backend.execute("playlist.edit.discard", {"editId": current["editId"]})
    assert error.value.code == "stale_edit"


def test_rename_duplicate_use_existing_saved_service(saved_set, monkeypatch) -> None:
    backend, original, _ = saved_set
    called = []
    rename, duplicate = backend.saved.rename_playlist, backend.saved.duplicate_playlist
    monkeypatch.setattr(backend.saved, "rename_playlist", lambda *args: (called.append("rename"), rename(*args))[-1])
    monkeypatch.setattr(
        backend.saved, "duplicate_playlist", lambda *args: (called.append("duplicate"), duplicate(*args))[-1]
    )
    renamed = backend.execute("playlist.rename", {"playlistId": original.id, "name": "Renamed"})
    copied = backend.execute("playlist.duplicate", {"playlistId": original.id})
    assert renamed["name"] == "Renamed"
    assert copied["name"] == "Renamed (copy)"
    assert copied["id"] != original.id
    assert copied["trackCount"] == len(original.track_paths)
    assert backend.playlists.get_by_id(copied["id"]).track_paths == original.track_paths
    assert called == ["rename", "duplicate"]


@pytest.mark.parametrize(
    "method,params",
    [
        ("playlist.rename", {"playlistId": True, "name": "x"}),
        ("playlist.rename", {"playlistId": 1, "name": " "}),
        ("playlist.rename", {"playlistId": 1, "name": "x" * 201}),
        ("playlist.duplicate", {"playlistId": -1}),
        ("playlist.edit.open", {"playlistId": "1"}),
        ("playlist.edit.open", {"playlistId": 2**63}),
        ("playlist.edit.discard", {"editId": "not-a-uuid"}),
        ("playlist.edit.open", {"playlistId": 1, "path": "/private"}),
    ],
)
def test_invalid_editor_inputs_fail_closed(saved_set, method, params) -> None:
    backend, _, _ = saved_set
    with pytest.raises(BackendError) as error:
        backend.execute(method, params)
    assert error.value.code == "invalid_params"


@pytest.mark.parametrize("method", ["playlist.save", "playlist.edit.save", "playlist.rename", "playlist.duplicate"])
def test_started_mutations_never_acknowledge_cancellation(tmp_path: Path, method: str) -> None:
    started, release = threading.Event(), threading.Event()

    class SlowBackend(HeadlessBackend):
        def execute(self, method, params, *, cancellation_token=None, progress=None):
            started.set()
            assert release.wait(5)
            assert cancellation_token is not None and not cancellation_token.is_cancelled
            return {"committed": True}

    output = io.StringIO()
    server = JsonlServer(SlowBackend(tmp_path), output)
    job_id = str(uuid4())
    server.process_line(request(method, {}, job_id))
    assert started.wait(5)
    server.process_line(request("cancel", {"jobId": job_id}))
    release.set()
    server.close()
    result = messages(output)
    assert result[0]["result"] == {"cancelled": False}
    assert result[1]["result"] == {"committed": True}


def test_cached_metadata_preview_keeps_missing_file_marker_like_qt(saved_set) -> None:
    backend, original, root = saved_set
    (root / "1.flac").unlink()
    opened = backend.execute("playlist.edit.open", {"playlistId": original.id})
    preview = backend.execute(
        "playlist.edit.preview", {"editId": opened["editId"], "trackIds": ids(opened), "request": "raise energy"}
    )
    assert preview["tracks"][1]["missing"] is True
    assert backend.playlists.get_by_id(original.id) == original


def test_stale_preview_after_domain_assessment_is_rejected(saved_set, monkeypatch) -> None:
    import xfinaudio.headless.playlist_editor as editor

    backend, original, _ = saved_set
    opened = backend.execute("playlist.edit.open", {"playlistId": original.id})
    assess = editor.assess_playlist_edit

    def concurrent_change(*args, **kwargs):
        result = assess(*args, **kwargs)
        backend.playlists.update_name(original.id, "Changed during preview")
        return result

    monkeypatch.setattr(editor, "assess_playlist_edit", concurrent_change)
    with pytest.raises(BackendError) as error:
        backend.execute(
            "playlist.edit.preview", {"editId": opened["editId"], "trackIds": ids(opened), "request": "raise energy"}
        )
    assert error.value.code == "stale_edit"


@pytest.mark.parametrize("order", [None, "opaque", [True], [{}], [1], ["x" * 65]])
def test_invalid_draft_shapes_reject_without_writing(saved_set, order) -> None:
    backend, original, _ = saved_set
    opened = backend.execute("playlist.edit.open", {"playlistId": original.id})
    with pytest.raises(BackendError) as error:
        backend.execute("playlist.edit.save", {"editId": opened["editId"], "name": "No", "trackIds": order})
    assert error.value.code == "invalid_params"
    assert backend.playlists.get_by_id(original.id) == original


@pytest.mark.parametrize("command", [" ", "x" * 2001, "raise energy\x00", True])
def test_invalid_preview_request_is_bounded(saved_set, command) -> None:
    backend, original, _ = saved_set
    opened = backend.execute("playlist.edit.open", {"playlistId": original.id})
    with pytest.raises(BackendError) as error:
        backend.execute(
            "playlist.edit.preview", {"editId": opened["editId"], "trackIds": ids(opened), "request": command}
        )
    assert error.value.code == "invalid_params"
    assert backend.playlists.get_by_id(original.id) == original


@pytest.mark.parametrize("command", ["do something magical", "shorten to 1 track"])
def test_unsupported_or_musically_blocked_preview_keeps_saved_order(saved_set, command) -> None:
    backend, original, _ = saved_set
    opened = backend.execute("playlist.edit.open", {"playlistId": original.id})
    with pytest.raises(BackendError) as error:
        backend.execute(
            "playlist.edit.preview", {"editId": opened["editId"], "trackIds": ids(opened), "request": command}
        )
    assert error.value.code == "invalid_edit"
    assert backend.playlists.get_by_id(original.id) == original


def test_save_racing_external_writer_rejects_without_partial_rename(saved_set, monkeypatch) -> None:
    backend, original, _ = saved_set
    opened = backend.execute("playlist.edit.open", {"playlistId": original.id})
    commit = backend.playlists.compare_and_update

    def concurrent_change(*args, **kwargs):
        backend.playlists.update_tracks(original.id, original.track_paths[:2])
        return commit(*args, **kwargs)

    monkeypatch.setattr(backend.playlists, "compare_and_update", concurrent_change)
    with pytest.raises(BackendError) as error:
        backend.execute(
            "playlist.edit.save",
            {"editId": opened["editId"], "name": "No partial rename", "trackIds": ids(opened)[::-1]},
        )
    assert error.value.code == "stale_edit"
    saved = backend.playlists.get_by_id(original.id)
    assert saved.name == original.name
    assert saved.track_paths == original.track_paths[:2]
