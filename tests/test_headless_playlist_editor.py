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
    assert "Validación del motor (estrategia de construcción)" in preview["assessment"]["description"]
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


# --- I1.7 / I1.8 proposal-bound exact-order save ------------------------------


def improvement_setup(tmp_path: Path):
    """A scanned playlist whose replacement pool is local to the same backend."""
    root = tmp_path / "music"
    for index in range(5):
        tagged_flac(root / f"{index}.flac", index)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    paths = [str(root / f"{index}.flac") for index in range(5)]
    playlist = backend.playlists.create("Improvement set", paths[:3])
    opened = backend.execute("playlist.edit.open", {"playlistId": playlist.id})
    return backend, playlist, opened, paths


def public_ids(paths) -> list[str]:
    return [hashlib.sha256(str(path).encode("utf-8")).hexdigest() for path in paths]


def bind_improvement(backend, opened, *, include_replacements: bool = True):
    draft_ids = ids(opened)
    candidate_set = backend.editor.improvement_candidates(
        opened["editId"], draft_ids, include_replacements=include_replacements
    )
    ordered = list(candidate_set.draft_tokens)
    if candidate_set.replacement_tokens:
        ordered[-1] = candidate_set.replacement_tokens[0]
    proposal = backend.editor.bind_improvement_proposal(opened["editId"], candidate_set, ordered, draft_ids=draft_ids)
    return candidate_set, proposal


def save_improvement(backend, opened, proposal, **overrides):
    params = {
        "editId": opened["editId"],
        "name": "AI improvement",
        "proposalId": proposal.proposal_id,
        "digest": proposal.digest,
        "draftIds": public_ids(proposal.after_paths),
    }
    params.update(overrides)
    return backend.execute("playlist.edit.save_improvement", params)


def test_improvement_candidates_only_authorize_replacements_after_opt_in(tmp_path: Path) -> None:
    backend, _, opened, paths = improvement_setup(tmp_path)
    draft_ids = ids(opened)
    without_pool = backend.editor.improvement_candidates(opened["editId"], draft_ids)
    with_pool = backend.editor.improvement_candidates(opened["editId"], draft_ids, include_replacements=True)
    assert without_pool.replacement_tokens == ()
    assert [without_pool.paths_by_token[token] for token in without_pool.draft_tokens] == paths[:3]
    assert with_pool.replacement_tokens
    assert {with_pool.paths_by_token[token] for token in with_pool.replacement_tokens} == set(paths[3:])


def test_dedicated_improvement_save_persists_exactly_the_validated_order(tmp_path: Path) -> None:
    backend, playlist, opened, paths = improvement_setup(tmp_path)
    assert playlist.id is not None
    files = {path: hashlib.sha256(Path(path).read_bytes()).digest() for path in paths}
    candidate_set, proposal = bind_improvement(backend, opened)
    assert proposal.after_paths[-1] == candidate_set.paths_by_token[candidate_set.replacement_tokens[0]]
    saved = save_improvement(backend, opened, proposal, name="AI improved")
    persisted = backend.playlists.get_by_id(playlist.id)
    assert persisted.name == "AI improved"
    assert persisted.track_paths == list(proposal.after_paths)
    assert ids(saved) == public_ids(proposal.after_paths)
    assert saved["editId"] != opened["editId"]
    assert proposal.after_paths[-1] in paths[3:]
    assert all(hashlib.sha256(Path(path).read_bytes()).digest() == digest for path, digest in files.items())


def test_manual_save_still_rejects_the_replacement_draft(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    candidate_set, _ = bind_improvement(backend, opened)
    replacement = candidate_set.paths_by_token[candidate_set.replacement_tokens[0]]
    with pytest.raises(BackendError) as error:
        backend.execute(
            "playlist.edit.save",
            {
                "editId": opened["editId"],
                "name": "Manual add",
                "trackIds": [*ids(opened), public_ids([replacement])[0]],
            },
        )
    assert error.value.code == "invalid_edit"
    assert backend.playlists.get_by_id(playlist.id) == playlist


def test_manual_reorder_save_after_binding_invalidates_the_improvement(tmp_path: Path) -> None:
    backend, playlist, opened, paths = improvement_setup(tmp_path)
    assert playlist.id is not None
    _, proposal = bind_improvement(backend, opened)
    backend.execute(
        "playlist.edit.save",
        {"editId": opened["editId"], "name": "Manual", "trackIds": ids(opened)[::-1]},
    )
    assert backend.playlists.get_by_id(playlist.id).track_paths == paths[:3][::-1]
    with pytest.raises(BackendError) as error:
        save_improvement(backend, opened, proposal)
    assert error.value.code == "stale_edit"
    assert backend.playlists.get_by_id(playlist.id).track_paths == paths[:3][::-1]


@pytest.mark.parametrize("field", ["proposalId", "digest"])
def test_bound_save_rejects_mismatched_proposal_identity_without_write(tmp_path: Path, field: str) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    _, proposal = bind_improvement(backend, opened)
    with pytest.raises(BackendError) as error:
        save_improvement(backend, opened, proposal, **{field: "mismatch"})
    assert error.value.code == "invalid_edit"
    assert backend.playlists.get_by_id(playlist.id) == playlist


def test_bound_save_rejects_a_mutated_draft_order_without_write(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    _, proposal = bind_improvement(backend, opened)
    with pytest.raises(BackendError) as error:
        save_improvement(backend, opened, proposal, draftIds=list(reversed(public_ids(proposal.after_paths))))
    assert error.value.code == "stale_edit"
    assert backend.playlists.get_by_id(playlist.id) == playlist


def test_bound_save_rejects_an_extra_draft_track_without_write(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    _, proposal = bind_improvement(backend, opened)
    with pytest.raises(BackendError) as error:
        save_improvement(
            backend,
            opened,
            proposal,
            draftIds=[*public_ids(proposal.after_paths), *public_ids(["/music/not-authorized.flac"])],
        )
    assert error.value.code == "stale_edit"
    assert backend.playlists.get_by_id(playlist.id) == playlist


def test_bound_save_rejects_a_stale_saved_revision_without_write(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    _, proposal = bind_improvement(backend, opened)
    backend.playlists.update_name(playlist.id, "External rename")
    with pytest.raises(BackendError) as error:
        save_improvement(backend, opened, proposal)
    assert error.value.code == "stale_edit"
    assert backend.playlists.get_by_id(playlist.id).name == "External rename"


def test_bound_save_rejects_a_swapped_edit_session_without_write(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    _, proposal = bind_improvement(backend, opened)
    backend.execute("playlist.edit.open", {"playlistId": playlist.id})
    with pytest.raises(BackendError) as error:
        save_improvement(backend, opened, proposal)
    assert error.value.code == "stale_edit"
    assert backend.playlists.get_by_id(playlist.id) == playlist


def test_bound_save_requires_a_locally_bound_proposal(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    with pytest.raises(BackendError) as error:
        backend.execute(
            "playlist.edit.save_improvement",
            {
                "editId": opened["editId"],
                "name": "Forged",
                "proposalId": str(uuid4()),
                "digest": "0" * 64,
                "draftIds": ids(opened),
            },
        )
    assert error.value.code == "invalid_edit"
    assert backend.playlists.get_by_id(playlist.id) == playlist


def test_bound_save_rejects_a_raw_path_list(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    _, proposal = bind_improvement(backend, opened)
    with pytest.raises(BackendError) as error:
        save_improvement(backend, opened, proposal, trackIds=ids(opened))
    assert error.value.code == "invalid_params"
    assert backend.playlists.get_by_id(playlist.id) == playlist


def test_bind_rejects_a_candidate_set_from_a_different_draft(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    draft_ids = ids(opened)
    candidate_set = backend.editor.improvement_candidates(opened["editId"], draft_ids, include_replacements=True)
    with pytest.raises(BackendError) as error:
        backend.editor.bind_improvement_proposal(
            opened["editId"],
            candidate_set,
            list(candidate_set.draft_tokens),
            draft_ids=list(reversed(draft_ids)),
        )
    assert error.value.code == "stale_edit"
    assert backend.playlists.get_by_id(playlist.id) == playlist


def test_bound_save_revalidates_the_stored_order_before_writing(tmp_path: Path) -> None:
    from dataclasses import replace

    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    _, proposal = bind_improvement(backend, opened)
    session = backend.editor.session
    assert session is not None
    tampered = replace(proposal, after_paths=tuple(reversed(proposal.after_paths)))
    backend.editor.session = replace(session, proposal=tampered)
    with pytest.raises(BackendError) as error:
        save_improvement(backend, opened, proposal)
    assert error.value.code == "invalid_edit"
    assert backend.playlists.get_by_id(playlist.id) == playlist


@pytest.mark.parametrize("method", ["playlist.edit.propose_improvement", "playlist.edit.improvement"])
def test_no_ipc_command_creates_an_arbitrary_authority_proposal(tmp_path: Path, method: str) -> None:
    backend, _, _, _ = improvement_setup(tmp_path)
    with pytest.raises(BackendError) as error:
        backend.execute(method, {})
    assert error.value.code == "unknown_method"


def test_improvement_candidates_reject_an_unknown_renderer_track(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    forged = [*ids(opened), *public_ids(["/music/not-scanned.flac"])]
    with pytest.raises(BackendError) as error:
        backend.editor.improvement_candidates(opened["editId"], forged, include_replacements=True)
    assert error.value.code == "invalid_edit"
    assert backend.playlists.get_by_id(playlist.id) == playlist


def test_bind_rejects_an_order_below_the_minimum(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    draft_ids = ids(opened)
    candidate_set = backend.editor.improvement_candidates(opened["editId"], draft_ids)
    with pytest.raises(BackendError) as error:
        backend.editor.bind_improvement_proposal(
            opened["editId"], candidate_set, [candidate_set.draft_tokens[0]], draft_ids=draft_ids
        )
    assert error.value.code == "invalid_improvement"
    assert backend.playlists.get_by_id(playlist.id) == playlist


def test_improvement_save_persists_a_draft_only_reorder(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    draft_ids = ids(opened)
    candidate_set = backend.editor.improvement_candidates(opened["editId"], draft_ids)
    proposal = backend.editor.bind_improvement_proposal(
        opened["editId"], candidate_set, list(reversed(candidate_set.draft_tokens)), draft_ids=draft_ids
    )
    saved = save_improvement(backend, opened, proposal)
    assert backend.playlists.get_by_id(playlist.id).track_paths == list(proposal.after_paths)
    assert ids(saved) == list(reversed(draft_ids))


def test_improvement_save_can_replace_the_whole_draft_with_pool_tracks(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    draft_ids = ids(opened)
    candidate_set = backend.editor.improvement_candidates(opened["editId"], draft_ids, include_replacements=True)
    ordered = list(candidate_set.replacement_tokens[:2])
    assert len(ordered) == 2
    proposal = backend.editor.bind_improvement_proposal(opened["editId"], candidate_set, ordered, draft_ids=draft_ids)
    assert proposal.after_paths == tuple(
        candidate_set.paths_by_token[token] for token in candidate_set.replacement_tokens[:2]
    )
    saved = save_improvement(backend, opened, proposal)
    assert backend.playlists.get_by_id(playlist.id).track_paths == list(proposal.after_paths)
    assert ids(saved) == public_ids(proposal.after_paths)


def test_discard_clears_the_bound_improvement_proposal(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    _, proposal = bind_improvement(backend, opened)
    backend.execute("playlist.edit.discard", {"editId": opened["editId"]})
    with pytest.raises(BackendError) as error:
        save_improvement(backend, opened, proposal)
    assert error.value.code == "stale_edit"
    assert backend.playlists.get_by_id(playlist.id) == playlist


def test_bound_save_rejects_a_duplicated_draft_track_without_write(tmp_path: Path) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    _, proposal = bind_improvement(backend, opened)
    applied = public_ids(proposal.after_paths)
    with pytest.raises(BackendError) as error:
        save_improvement(backend, opened, proposal, draftIds=[applied[0], applied[0]])
    assert error.value.code == "invalid_edit"
    assert backend.playlists.get_by_id(playlist.id) == playlist


def test_improvement_save_racing_external_writer_rejects_without_partial_write(tmp_path: Path, monkeypatch) -> None:
    backend, playlist, opened, _ = improvement_setup(tmp_path)
    assert playlist.id is not None
    playlist_id = playlist.id
    _, proposal = bind_improvement(backend, opened)
    commit = backend.playlists.compare_and_update

    def concurrent_change(*args, **kwargs):
        backend.playlists.update_tracks(playlist_id, playlist.track_paths[:2])
        return commit(*args, **kwargs)

    monkeypatch.setattr(backend.playlists, "compare_and_update", concurrent_change)
    with pytest.raises(BackendError) as error:
        save_improvement(backend, opened, proposal)
    assert error.value.code == "stale_edit"
    saved = backend.playlists.get_by_id(playlist.id)
    assert saved.name == playlist.name
    assert saved.track_paths == playlist.track_paths[:2]
