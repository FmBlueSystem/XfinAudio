"""Confirmed Serato export uses disposable fixtures only, with no implicit discovery."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from tests.test_headless_backend import tagged_flac
from xfinaudio.exporting.serato_crate import parse_serato_crate_bytes
from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.headless.serato_safety import volume_root


@pytest.fixture
def export_set(tmp_path):
    root = tmp_path / "music"
    for index in range(3):
        tagged_flac(root / f"{index}.flac", index)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    playlist = backend.playlists.create("Saved set", [str(root / f"{index}.flac") for index in (2, 0, 1)])
    serato = tmp_path / "destination" / "_Serato_"
    (serato / "Subcrates").mkdir(parents=True)
    (serato / "database V2").write_bytes(b"DO NOT CHANGE DATABASE")
    grant = backend.execute("serato.registerDestination", {"seratoRoot": str(serato)})
    return backend, playlist, root, serato, grant


def preview(fixture, **updates):
    backend, playlist, _, _, grant = fixture
    return backend.execute(
        "serato.preview",
        {
            "source": {"kind": "saved", "playlistId": playlist.id},
            "destinationId": grant["destinationId"],
            "name": "Fixture set",
            **updates,
        },
    )


def commit(backend, item):
    return backend.execute("serato.commit", {"previewId": item["previewId"], "confirmed": True})


def files(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_preview_is_read_only_private_and_preserves_exact_saved_order(export_set):
    backend, playlist, music, serato, grant = export_set
    before = files(music.parent)
    item = preview(export_set)
    assert item["canCommit"] is True
    assert item["readiness"] in {"ready", "needs_review"}
    assert len(item["sourceRevision"]) == 64
    assert str(UUID(item["previewId"])) == item["previewId"]
    assert item["filename"] == "Fixture set.crate"
    assert item["trackCount"] == 3
    assert [track["id"] for track in item["tracks"]] == [
        hashlib.sha256(path.encode()).hexdigest() for path in playlist.track_paths
    ]
    assert item["backup"] == {"required": False}
    assert files(music.parent) == before
    summary = backend.execute("serato.confirmation", {"previewId": item["previewId"]})
    assert summary == item
    assert str(music.parent) not in json.dumps([grant, item, summary])


def test_confirmed_write_reuses_real_serializer_and_is_idempotent(export_set):
    backend, playlist, music, serato, _ = export_set
    before_audio, before_db = files(music), (serato / "database V2").read_bytes()
    item = preview(export_set)
    receipt = commit(backend, item)
    crate = serato / "Subcrates" / item["filename"]
    assert parse_serato_crate_bytes(crate.read_bytes()).paths == tuple(
        Path(path).relative_to(volume_root(Path(path))).as_posix() for path in playlist.track_paths
    )
    assert receipt["validated"] is True and receipt["trackCount"] == 3
    assert commit(backend, item) == receipt
    assert len(list(crate.parent.iterdir())) == 1
    assert backend.execute("serato.receipt.resolve", {"receiptId": receipt["receiptId"]}) == {"path": str(crate)}
    assert str(music.parent) not in json.dumps(receipt)
    assert files(music) == before_audio and (serato / "database V2").read_bytes() == before_db


@pytest.mark.parametrize(
    "name", ["../escape", "/absolute", "a/b", "a\\b", ".", "..", "a\n", "a\x00", "a\x7f", "é" * 130]
)
def test_invalid_names_rejected_without_writes(export_set, name):
    with pytest.raises(BackendError) as error:
        preview(export_set, name=name)
    assert error.value.code == "invalid_params"
    assert not list(export_set[3].joinpath("Subcrates").iterdir())


@pytest.mark.parametrize(
    "source",
    [
        {"kind": "saved", "playlistId": True},
        {"kind": "saved", "playlistId": 0},
        {"kind": "saved", "playlistId": 2**80},
        {"kind": "saved", "playlistId": 1, "path": "/tmp"},
        {"kind": "review", "reviewId": "no"},
        {"kind": "unknown"},
        None,
    ],
)
def test_invalid_source_schemas_fail_closed(export_set, source):
    with pytest.raises(BackendError) as error:
        preview(export_set, source=source)
    assert error.value.code == "invalid_params"


def test_confirmation_and_unknown_fields_are_not_renderer_controlled(export_set):
    backend = export_set[0]
    item = preview(export_set)
    for params in (
        {"previewId": item["previewId"]},
        {"previewId": item["previewId"], "confirmed": 1},
        {"previewId": item["previewId"], "confirmed": True, "path": "/tmp"},
    ):
        with pytest.raises(BackendError):
            backend.execute("serato.commit", params)
    for method, params in (
        ("serato.preview", {"source": {}, "destinationId": str(uuid4())}),
        ("serato.confirmation", {"previewId": str(uuid4())}),
        ("serato.receipt.resolve", {"receiptId": str(uuid4())}),
    ):
        with pytest.raises(BackendError):
            backend.execute(method, params)
    assert not list(export_set[3].joinpath("Subcrates").iterdir())


@pytest.mark.parametrize("change", ["rename", "reorder", "metadata", "audio", "remove", "symlink", "review"])
def test_changed_source_cannot_commit(export_set, change):
    backend, playlist, music, serato, _ = export_set
    item = preview(export_set)
    if change == "rename":
        backend.saved.rename_playlist(playlist.id, "Changed")
    elif change == "reorder":
        backend.playlists.compare_and_update(playlist, name=playlist.name, track_paths=playlist.track_paths[::-1])
    elif change == "metadata":
        records = backend.repository.list_display_tracks()
        backend.repository.save_scan_results([records[0].model_copy(update={"bpm": 140.0})])
    elif change == "audio":
        with (music / "0.flac").open("ab") as handle:
            handle.write(b"changed")
    elif change == "remove":
        (music / "0.flac").unlink()
    elif change == "symlink":
        (music / "0.flac").unlink()
        (music / "0.flac").symlink_to(music / "1.flac")
    else:
        reviewed = backend.execute("prep.generate", {"name": "Review", "targetTrackCount": 3})
        item = preview(export_set, source={"kind": "review", "reviewId": reviewed["reviewId"]})
        backend.invalidate_review()
    with pytest.raises(BackendError) as error:
        commit(backend, item)
    assert error.value.code in {"stale_source", "stale_review"}
    assert not list(serato.joinpath("Subcrates").iterdir())


def test_missing_saved_tracks_remain_visible_and_blocked(export_set):
    backend, playlist, music, serato, _ = export_set
    (music / "0.flac").unlink()
    item = preview(export_set)
    assert item["trackCount"] == len(item["tracks"]) == len(playlist.track_paths)
    assert item["readiness"] == "blocked" and not item["canCommit"] and item["blockers"]
    with pytest.raises(BackendError) as error:
        commit(backend, item)
    assert error.value.code == "blocked_export"
    assert not list(serato.joinpath("Subcrates").iterdir())


@pytest.mark.parametrize(
    "change", ["new_collision", "changed_target", "parent_swap", "root_swap", "target_link", "backup_link"]
)
def test_destination_changes_require_new_preview(export_set, change):
    backend, _, _, serato, _ = export_set
    target = serato / "Subcrates" / "Fixture set.crate"
    if change == "changed_target":
        target.write_bytes(b"previous")
    item = preview(export_set)
    if change in {"new_collision", "changed_target"}:
        target.write_bytes(b"other writer")
    elif change in {"parent_swap", "root_swap"}:
        selected = target.parent if change == "parent_swap" else serato
        selected.rename(selected.with_name(selected.name + "-old"))
        selected.mkdir()
    else:
        leaf = target if change == "target_link" else target.with_name(target.name + ".bak")
        leaf.symlink_to(serato / "database V2")
    before = files(serato)
    with pytest.raises(BackendError) as error:
        commit(backend, item)
    assert error.value.code == "stale_destination"
    assert files(serato) == before


def test_overwrite_requires_bound_backup_and_keeps_database(export_set):
    backend, _, _, serato, _ = export_set
    target = serato / "Subcrates" / "Fixture set.crate"
    target.write_bytes(b"previous crate")
    item = preview(export_set)
    assert item["backup"] == {"required": True}
    receipt = commit(backend, item)
    assert receipt["backupCreated"] is True
    assert target.with_name(target.name + ".bak").read_bytes() == b"previous crate"
    assert (serato / "database V2").read_bytes() == b"DO NOT CHANGE DATABASE"


def test_destination_registration_rejects_symlink_ancestors(export_set):
    backend, _, music, serato, _ = export_set
    linked = music.parent / "linked"
    linked.symlink_to(serato.parent, target_is_directory=True)
    for root in (linked / "_Serato_", serato / "Subcrates", Path("relative")):
        with pytest.raises(BackendError) as error:
            backend.execute("serato.registerDestination", {"seratoRoot": str(root)})
        assert error.value.code == "invalid_destination"


def test_needs_review_allows_confirmation_but_fresh_blockers_do_not(export_set):
    backend, _, _, serato, _ = export_set
    tracks = backend.repository.list_display_tracks()
    backend.repository.save_scan_results([tracks[0].model_copy(update={"energy_level": 10})])
    item = preview(export_set)
    assert item["readiness"] == "needs_review" and item["canCommit"] and item["warnings"]
    assert commit(backend, item)["validated"]
    backend.repository.save_scan_results([tracks[0].model_copy(update={"bpm": None})])
    blocked = preview(export_set)
    assert blocked["readiness"] == "blocked" and not blocked["canCommit"]
    with pytest.raises(BackendError):
        backend.execute("serato.confirmation", {"previewId": blocked["previewId"]})
    assert len(list(serato.joinpath("Subcrates").glob("*.crate"))) == 1


def test_current_review_uses_actual_recommendation_and_generated_naming(export_set):
    backend, _, _, serato, _ = export_set
    review = backend.execute("prep.generate", {"name": "Review", "targetTrackCount": 3})
    params = {
        "source": {"kind": "review", "reviewId": review["reviewId"]},
        "destinationId": export_set[4]["destinationId"],
    }
    item = backend.execute("serato.preview", params)
    assert item["filename"].startswith("XfinAudio%%Prep Copilot%%")
    assert "%%Balanced%%" in item["filename"]
    assert [track["id"] for track in item["tracks"]] == [track["id"] for track in review["tracks"]]
    commit(backend, item)
    next_item = backend.execute("serato.preview", params)
    assert next_item["filename"] == item["filename"].removesuffix(".crate") + "-2.crate"
    assert not next_item["backup"]["required"]
    assert len(list(serato.joinpath("Subcrates").glob("*.crate"))) == 1


@pytest.mark.parametrize("external", [False, True])
def test_home_and_external_volume_references_do_not_use_destination_parent(tmp_path, monkeypatch, external):
    volume = tmp_path / "fixture-volume"
    music = volume / ("Music" if external else "Users/freddy/Music") / "Source"
    for index in range(2):
        tagged_flac(music / f"{index}.flac", index)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(music)})
    playlist = backend.playlists.create("Volume", [str(music / "1.flac"), str(music / "0.flac")])
    serato = volume / ("_Serato_" if external else "Users/freddy/Music/_Serato_")
    (serato / "Subcrates").mkdir(parents=True)
    monkeypatch.setattr("xfinaudio.headless.serato_export.volume_root", lambda path: volume)
    grant = backend.execute("serato.registerDestination", {"seratoRoot": str(serato)})
    item = preview((backend, playlist, music, serato, grant))
    commit(backend, item)
    references = parse_serato_crate_bytes((serato / "Subcrates" / item["filename"]).read_bytes()).paths
    assert references == tuple(Path(path).relative_to(volume).as_posix() for path in playlist.track_paths)
    assert [(volume / reference).resolve() for reference in references] == list(map(Path, playlist.track_paths))
    if not external:
        assert all(reference.startswith("Users/freddy/") for reference in references)


@pytest.mark.parametrize("mixed", [False, True])
def test_mixed_or_unmatched_source_volumes_block_without_dropping(export_set, monkeypatch, mixed):
    backend, _, music, serato, _ = export_set
    source_volume = music.parent
    other_volume = music.parent / "other-volume"
    monkeypatch.setattr(
        "xfinaudio.headless.serato_export.volume_root",
        lambda path: other_volume if path == (music / "0.flac" if mixed else serato) else source_volume,
    )
    item = preview(export_set)
    assert item["trackCount"] == len(item["tracks"]) == 3
    assert item["readiness"] == "blocked" and not item["canCommit"]
    with pytest.raises(BackendError):
        commit(backend, item)
    assert not list(serato.joinpath("Subcrates").iterdir())


@pytest.mark.parametrize("existing", [False, True])
def test_readback_failure_recovers_original_state(export_set, monkeypatch, existing):
    backend, _, _, serato, _ = export_set
    target = serato / "Subcrates" / "Fixture set.crate"
    if existing:
        target.write_bytes(b"original crate")
    item = preview(export_set)
    monkeypatch.setattr("xfinaudio.exporting.serato_crate.validate_serato_crate_file", lambda *args, **kwargs: False)
    with pytest.raises(BackendError) as error:
        commit(backend, item)
    assert error.value.code == "export_failed"
    assert str(serato) not in str(error.value)
    if existing:
        assert target.read_bytes() == target.with_name(target.name + ".bak").read_bytes() == b"original crate"
    else:
        assert not target.exists()
    assert (serato / "database V2").read_bytes() == b"DO NOT CHANGE DATABASE"


def test_ancestor_swap_during_write_rolls_back_inside_pinned_directory(export_set, monkeypatch):
    from xfinaudio.exporting import serato_crate

    backend, _, music, serato, _ = export_set
    item = preview(export_set)
    outside = music.parent / "outside"
    outside.mkdir()
    sentinel = outside / item["filename"]
    sentinel.write_bytes(b"UNRELATED")
    original_validate = serato_crate.validate_serato_crate_file
    moved = serato / "Subcrates-old"

    def swap(plan, **kwargs):
        result = original_validate(plan, **kwargs)
        (serato / "Subcrates").rename(moved)
        (serato / "Subcrates").symlink_to(outside, target_is_directory=True)
        return result

    monkeypatch.setattr(serato_crate, "validate_serato_crate_file", swap)
    with pytest.raises(BackendError) as error:
        commit(backend, item)
    assert error.value.code == "stale_destination"
    assert not list(moved.iterdir())
    assert sentinel.read_bytes() == b"UNRELATED"
    assert (serato / "database V2").read_bytes() == b"DO NOT CHANGE DATABASE"


def test_public_preview_cannot_mutate_server_plan(export_set):
    backend, playlist, _, serato, _ = export_set
    item = preview(export_set)
    item["filename"] = "forged.crate"
    item["tracks"].clear()
    item["canCommit"] = False
    result = commit(backend, item)
    assert result["filename"] == "Fixture set.crate" and result["trackCount"] == len(playlist.track_paths)
    assert not (serato / "Subcrates" / "forged.crate").exists()


def test_qt_provider_and_network_firewall_covers_real_export(tmp_path):
    script = r"""
import importlib.abc, sys, socket, subprocess
from pathlib import Path
class Firewall(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('PySide6', 'xfinaudio.desktop', 'xfinaudio.ai')):
            raise AssertionError(fullname)
sys.meta_path.insert(0, Firewall())
def forbidden(*args, **kwargs):
    raise AssertionError('No network/provider/subprocess calls')
socket.socket.connect = forbidden
subprocess.Popen = forbidden
from tests.test_headless_backend import tagged_flac
from xfinaudio.headless.backend import HeadlessBackend
root = Path(sys.argv[1])
music = root / 'music'
for index in range(2):
    tagged_flac(music / f'{index}.flac', index)
backend = HeadlessBackend(root / 'data')
backend.execute('library.scan', {'root': str(music)})
playlist = backend.playlists.create('Fixture', [str(music / f'{i}.flac') for i in range(2)])
serato = root / '_Serato_'
(serato / 'Subcrates').mkdir(parents=True)
grant = backend.execute('serato.registerDestination', {'seratoRoot': str(serato)})
item = backend.execute('serato.preview', {
    'source': {'kind': 'saved', 'playlistId': playlist.id}, 'destinationId': grant['destinationId']})
assert backend.execute('serato.commit', {'previewId': item['previewId'], 'confirmed': True})['validated']
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("kind", [[], {}, 1, True, ""])
def test_malformed_source_kind_is_a_safe_protocol_error(export_set, kind):
    with pytest.raises(BackendError) as error:
        preview(export_set, source={"kind": kind})
    assert error.value.code == "invalid_params"


def test_native_reconfirmation_of_completed_preview_is_idempotent(export_set):
    backend = export_set[0]
    item = preview(export_set)
    receipt = commit(backend, item)
    assert backend.execute("serato.confirmation", {"previewId": item["previewId"]}) == item
    assert commit(backend, item) == receipt


def test_receipt_reveal_rejects_content_changed_with_restored_size_and_mtime(export_set):
    backend, _, _, serato, _ = export_set
    item = preview(export_set)
    receipt = commit(backend, item)
    target = serato / "Subcrates" / item["filename"]
    before = target.stat()
    target.write_bytes(b"x" * before.st_size)
    os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
    with pytest.raises(BackendError) as error:
        backend.execute("serato.receipt.resolve", {"receiptId": receipt["receiptId"]})
    assert error.value.code == "stale_destination"


def test_long_valid_utf8_crate_name_uses_short_private_temporary_filename(export_set):
    item = preview(export_set, name="é" * 115)
    assert commit(export_set[0], item)["validated"] is True


def test_macos_home_volume_uses_system_root_despite_apfs_device_boundary(export_set, monkeypatch):
    from xfinaudio.headless import serato_safety

    # The Linux fixture is on a separate /tmp device, modelling a firmlink's
    # device change without requiring any real /Users or /Volumes directories.
    monkeypatch.setattr(sys, "platform", "darwin")
    assert serato_safety.volume_root(export_set[2] / "0.flac") == Path("/")
    assert serato_safety.volume_root(Path("/Volumes/DJDrive/Music/track.flac")) == Path("/Volumes/DJDrive")


def test_server_cancel_refuses_commit_and_shutdown_drains_publication(export_set, monkeypatch):
    import io
    import threading

    from tests.test_headless_protocol import messages, request
    from xfinaudio.headless import serato_export
    from xfinaudio.headless.server import JsonlServer

    backend = export_set[0]
    item = preview(export_set)
    entered, released, closing, closed = (threading.Event() for _ in range(4))
    original = serato_export.write_serato_crate

    def paused(*args, **kwargs):
        entered.set()
        assert released.wait(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(serato_export, "write_serato_crate", paused)
    output = io.StringIO()
    server = JsonlServer(backend, output)
    job_id = str(uuid4())
    server.process_line(
        request("serato.commit", {"previewId": item["previewId"], "confirmed": True}, request_id=job_id)
    )
    assert entered.wait(5)
    server.process_line(request("cancel", {"jobId": job_id}))
    assert messages(output)[-1]["result"] == {"cancelled": False}

    def close():
        closing.set()
        server.close()
        closed.set()

    closer = threading.Thread(target=close)
    closer.start()
    try:
        assert closing.wait(5)
        assert not closed.wait(0.05)
    finally:
        released.set()
        closer.join(5)
    assert closed.is_set()
    result = next(message for message in messages(output) if message.get("id") == job_id)
    assert result["ok"] and result["result"]["validated"]
    assert (export_set[3] / "Subcrates" / item["filename"]).is_file()


def test_headless_preview_rejects_oversized_target_without_reading_or_writing(export_set):
    backend, _, _, serato, _ = export_set
    target = serato / "Subcrates" / "Fixture set.crate"
    with target.open("wb") as handle:
        handle.truncate(16 * 1024 * 1024 + 1)
    with pytest.raises(BackendError) as failure:
        preview(export_set)
    assert failure.value.code == "invalid_destination"
    assert target.stat().st_size == 16 * 1024 * 1024 + 1
    assert list(target.parent.iterdir()) == [target]


def test_headless_export_rejects_more_than_500_references_before_assessment(export_set):
    backend, _, music, _, _ = export_set
    playlist = backend.playlists.create("Too large", [str(music / "0.flac")] * 501)
    with pytest.raises(BackendError) as failure:
        preview(export_set, source={"kind": "saved", "playlistId": playlist.id})
    assert failure.value.code == "export_too_large"


def test_headless_generated_payload_limit_fails_before_writes(export_set, monkeypatch):
    import xfinaudio.headless.serato_export as exports

    monkeypatch.setattr(exports, "MAX_ANCHORED_CRATE_BYTES", 1)
    with pytest.raises(BackendError):
        preview(export_set)
    assert list((export_set[3] / "Subcrates").iterdir()) == []
