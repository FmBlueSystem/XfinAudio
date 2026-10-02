"""Synthetic-only migration tests; no original HOME/library reads."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.legacy_import import recover_legacy_import
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_repository import PlaylistRepository
from xfinaudio.library.track_repository import TrackRepository


def fixture(tmp_path):
    source, destination = tmp_path / "legacy", tmp_path / "new"
    source.mkdir()
    destination.mkdir()
    repository = TrackRepository(source / "xfinaudio.sqlite3")
    repository.save_scan_results([TrackRecord(path="/never-open/music.flac", title="Title")])
    PlaylistRepository(source / "playlists.db").create("My Set", ["/never-open/music.flac"])
    (source / "settings.json").write_text(
        json.dumps(
            {
                "settings_version": 1,
                "audio": {"preview_volume": 0.4},
                "scoring": {"spectral_cohesion": 0.8},
                "ai": {"enabled": True, "env_file": "/never-open/credentials"},
                "library": {"watch_for_changes": True, "last_scan_folder": "/never-open"},
                "loudness": {"enabled": True},
            }
        )
    )
    backend = HeadlessBackend(destination)
    return source, backend, backend.legacy_import


def hashes(directory):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir() if p.is_file()}


def error(code, action):
    with pytest.raises(BackendError) as caught:
        action()
    assert caught.value.code == code


def test_preview_apply_preserves_original_and_requires_roots(tmp_path, monkeypatch):
    source, backend, service = fixture(tmp_path)
    before = hashes(source)
    original_stat = Path.stat

    def guarded(path, *args, **kwargs):
        assert not str(path).startswith("/never-open"), "Imported reference was accessed"
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", guarded)
    preview = service.execute("legacy.preview", {"source": str(source)})
    assert preview["trackCount"] == 1 and preview["playlistCount"] == 1
    assert preview["playlistNames"] == ["My Set"] and preview["requiresRootAuthorization"] is True
    assert "/never-open" not in json.dumps(preview)
    result = service.execute("legacy.apply", {"previewId": preview["previewId"], "confirmed": True})
    assert result["restartRequired"] is True and result["backupRetained"] is True
    assert backend.roots == [] and not (backend.data_dir / "roots.json").exists()
    assert backend.repository.list_display_tracks()[0].title == "Title"
    assert backend.playlists.list_summaries()[0].name == "My Set"
    settings = json.loads((backend.data_dir / "settings.json").read_text())
    assert settings["audio"]["preview_volume"] == 0.4 and settings["scoring"]["spectral_cohesion"] == 0.8
    assert not settings["ai"]["enabled"] and settings["ai"]["env_file"] is None
    assert not settings["loudness"]["enabled"] and not settings["library"]["watch_for_changes"]
    assert hashes(source) == before
    recover_legacy_import(backend.data_dir)
    assert backend.playlists.list_summaries()[0].name == "My Set"


@pytest.mark.parametrize("mutation", ["source", "destination", "settings", "roots"])
def test_changed_preview_or_nonempty_destination_never_imports(tmp_path, mutation):
    source, backend, service = fixture(tmp_path)
    preview = service.execute("legacy.preview", {"source": str(source)})
    if mutation == "source":
        (source / "settings.json").write_text("{}")
    if mutation == "destination":
        backend.playlists.create("New work", [])
    if mutation == "settings":
        (backend.data_dir / "settings.json").write_text("{}")
    if mutation == "roots":
        (backend.data_dir / "roots.json").write_text('["/never-open"]')
    error(
        "stale_legacy", lambda: service.execute("legacy.apply", {"previewId": preview["previewId"], "confirmed": True})
    )
    assert backend.repository.list_tracks() == []


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_sqlite_sidecars_fail_closed_even_empty(tmp_path, suffix):
    source, _, service = fixture(tmp_path)
    (source / ("xfinaudio.sqlite3" + suffix)).touch()
    error("legacy_source_active", lambda: service.execute("legacy.preview", {"source": str(source)}))


@pytest.mark.parametrize("kind", ["symlink", "parentlink", "corrupt", "schema", "oversize", "external_path"])
def test_unsafe_source_is_rejected(tmp_path, kind, monkeypatch):
    from xfinaudio.headless import legacy_source

    source, backend, service = fixture(tmp_path)
    if kind == "symlink":
        (source / "settings.json").rename(source / "hidden.json")
        (source / "settings.json").symlink_to(source / "hidden.json")
    if kind == "parentlink":
        link = tmp_path / "link"
        link.symlink_to(source, target_is_directory=True)
        source = link
    if kind == "corrupt":
        (source / "xfinaudio.sqlite3").write_bytes(b"bad")
    if kind == "schema":
        with sqlite3.connect(source / "xfinaudio.sqlite3") as db:
            db.execute("PRAGMA user_version=99")
    if kind == "oversize":
        monkeypatch.setattr(legacy_source, "MAX_DATABASE_BYTES", 100)
    if kind == "external_path":
        with sqlite3.connect(source / "xfinaudio.sqlite3") as db:
            db.execute("UPDATE tracks SET path='../escape.flac'")
    error("legacy_invalid", lambda: service.execute("legacy.preview", {"source": str(source)}))
    assert backend.repository.list_tracks() == []


def test_discard_and_token_replay_are_rejected(tmp_path):
    source, _, service = fixture(tmp_path)
    preview = service.execute("legacy.preview", {"source": str(source)})
    assert service.execute("legacy.discard", {"previewId": preview["previewId"]}) == {"discarded": True}
    error(
        "stale_legacy", lambda: service.execute("legacy.apply", {"previewId": preview["previewId"], "confirmed": True})
    )


def test_missing_confirmation_has_no_effect(tmp_path):
    source, backend, service = fixture(tmp_path)
    preview = service.execute("legacy.preview", {"source": str(source)})
    error(
        "confirmation_required",
        lambda: service.execute("legacy.apply", {"previewId": preview["previewId"], "confirmed": False}),
    )
    assert backend.playlists.list_summaries() == []


def test_late_destination_writer_is_never_overwritten(tmp_path, monkeypatch):
    from xfinaudio.headless import legacy_import

    source, backend, service = fixture(tmp_path)
    preview = service.execute("legacy.preview", {"source": str(source)})
    original = legacy_import.write_journal

    def race(root, record):
        original(root, record)
        if record["phase"] == "prepared":
            backend.playlists.create("Concurrent new work", [])

    monkeypatch.setattr(legacy_import, "write_journal", race)
    error(
        "legacy_recovery_required",
        lambda: service.execute("legacy.apply", {"previewId": preview["previewId"], "confirmed": True}),
    )
    assert [item.name for item in backend.playlists.list_summaries()] == ["Concurrent new work"]
    assert service.restart_required
    error("legacy_recovery_required", lambda: recover_legacy_import(backend.data_dir))


def test_partial_commit_rolls_back_and_retains_backup(tmp_path, monkeypatch):
    from xfinaudio.headless import legacy_import

    source, backend, service = fixture(tmp_path)
    before = hashes(backend.data_dir)
    preview = service.execute("legacy.preview", {"source": str(source)})
    original = legacy_import.durable_write

    def fail(path, content):
        if path.name == "commit-playlists.db":
            raise OSError("simulated disk full")
        original(path, content)

    monkeypatch.setattr(legacy_import, "durable_write", fail)
    error(
        "legacy_import_failed",
        lambda: service.execute("legacy.apply", {"previewId": preview["previewId"], "confirmed": True}),
    )
    for name, digest in before.items():
        assert hashes(backend.data_dir)[name] == digest
    assert not (backend.data_dir / "settings.json").exists()
    assert list(backend.data_dir.glob(".legacy-import-*/backup/tracks.db"))
    assert service.restart_required is False


def test_crash_recovery_before_repositories_open(tmp_path, monkeypatch):
    from xfinaudio.headless import legacy_import

    source, backend, service = fixture(tmp_path)
    before = hashes(backend.data_dir)
    preview = service.execute("legacy.preview", {"source": str(source)})
    original = legacy_import.durable_write

    def crash(path, content):
        if path.name == "commit-playlists.db":
            raise KeyboardInterrupt("simulated crash")
        original(path, content)

    monkeypatch.setattr(legacy_import, "durable_write", crash)
    with pytest.raises(KeyboardInterrupt):
        service.execute("legacy.apply", {"previewId": preview["previewId"], "confirmed": True})
    recover_legacy_import(backend.data_dir)
    for name, digest in before.items():
        assert hashes(backend.data_dir)[name] == digest
    assert backend.playlists.list_summaries() == []


def test_untrusted_recovery_manifest_never_follows_external_paths(tmp_path):
    _, backend, _ = fixture(tmp_path)
    (backend.data_dir / ".legacy-import-journal.json").write_text(
        json.dumps({"id": "../outside", "phase": "prepared", "before": {}, "after": {}})
    )
    error("legacy_recovery_required", lambda: recover_legacy_import(backend.data_dir))


def test_parent_symlink_swap_never_reads_unselected_data(tmp_path, monkeypatch):
    from xfinaudio.headless import legacy_source

    source, _, service = fixture(tmp_path)
    unselected = tmp_path / "unselected"
    unselected.mkdir()
    (unselected / "settings.json").write_text("secret sentinel")
    original = legacy_source.read_file
    read_values = []

    def race(path, limit, *args, **kwargs):
        if path == source / "settings.json" and source.is_dir() and not source.is_symlink():
            source.rename(tmp_path / "original")
            source.symlink_to(unselected, target_is_directory=True)
        value = original(path, limit, *args, **kwargs)
        read_values.append(value)
        return value

    monkeypatch.setattr(legacy_source, "read_file", race)
    error("legacy_invalid", lambda: service.execute("legacy.preview", {"source": str(source)}))
    assert b"secret sentinel" not in read_values


def test_real_backend_restart_quarantines_imported_paths_and_retains_cache(tmp_path):
    from xfinaudio.audio.spectral_profile import CURRENT_ANALYSIS_VERSION, SpectralProfile

    source, backend, _ = fixture(tmp_path)
    profile = SpectralProfile(
        red_ratio=0.8,
        green_ratio=0.15,
        blue_ratio=0.05,
        dominant_color="RED",
        centroid_hz=1000,
        rolloff_hz=2000,
        analysis_version=CURRENT_ANALYSIS_VERSION,
    )
    with sqlite3.connect(source / "xfinaudio.sqlite3") as database:
        database.execute(
            "UPDATE tracks SET spectral_profile_json=?,file_mtime_ns=123,file_size_bytes=456",
            (profile.model_dump_json(),),
        )
    preview = backend.execute("legacy.preview", {"source": str(source)})
    assert preview["cachedTrackCount"] == 1
    backend.execute("legacy.apply", {"previewId": preview["previewId"], "confirmed": True})
    error("legacy_restart_required", lambda: backend.execute("library.list", {}))
    restarted = HeadlessBackend(backend.data_dir)
    assert restarted.execute("library.list", {})["tracks"] == []
    assert restarted.repository.load_spectral_profile_cache(["/never-open/music.flac"])["/never-open/music.flac"][
        :2
    ] == (123, 456)
    assert restarted.playlists.list_summaries()[0].track_count == 1


def test_source_changes_during_commit_trigger_full_rollback(tmp_path, monkeypatch):
    from xfinaudio.headless import legacy_import

    source, backend, service = fixture(tmp_path)
    preview = service.execute("legacy.preview", {"source": str(source)})
    original = legacy_import.publish

    def race(old, new):
        original(old, new)
        if new.name == "playlists.db":
            (source / "settings.json").write_text("{}")

    monkeypatch.setattr(legacy_import, "publish", race)
    error(
        "legacy_import_failed",
        lambda: service.execute("legacy.apply", {"previewId": preview["previewId"], "confirmed": True}),
    )
    assert backend.repository.list_tracks() == [] and backend.playlists.list_summaries() == []


@pytest.mark.parametrize("change", ["profile", "trigger", "references", "date"])
def test_malformed_recoverable_content_fails_atomically(tmp_path, change):
    source, backend, service = fixture(tmp_path)
    if change in ("profile", "trigger"):
        with sqlite3.connect(source / "xfinaudio.sqlite3") as database:
            if change == "profile":
                database.execute("UPDATE tracks SET spectral_profile_json='{}'")
            else:
                database.execute("CREATE TRIGGER unexpected AFTER INSERT ON tracks BEGIN SELECT 1; END")
    else:
        with sqlite3.connect(source / "playlists.db") as database:
            if change == "references":
                database.execute("UPDATE playlist_tracks SET position=8")
            else:
                database.execute("UPDATE playlists SET created_at='bad'")
    error("legacy_invalid", lambda: service.execute("legacy.preview", {"source": str(source)}))
    assert backend.repository.list_tracks() == []


def test_late_root_grant_aborts_instead_of_authorizing_imported_paths(tmp_path, monkeypatch):
    from xfinaudio.headless import legacy_import

    source, backend, service = fixture(tmp_path)
    preview = service.execute("legacy.preview", {"source": str(source)})
    original = legacy_import.publish

    def race(old, new):
        original(old, new)
        if new.name == "tracks.db":
            (backend.data_dir / "roots.json").write_text('["/never-open"]')

    monkeypatch.setattr(legacy_import, "publish", race)
    error(
        "legacy_import_failed",
        lambda: service.execute("legacy.apply", {"previewId": preview["previewId"], "confirmed": True}),
    )
    assert backend.repository.list_tracks() == []


def test_failure_after_durable_commit_never_claims_rollback(tmp_path, monkeypatch):
    from xfinaudio.headless import legacy_import

    source, backend, service = fixture(tmp_path)
    preview = service.execute("legacy.preview", {"source": str(source)})
    original = legacy_import.write_journal

    def fail_after_commit(root, record):
        original(root, record)
        if record["phase"] == "committed":
            raise OSError("simulated final sync error")

    monkeypatch.setattr(legacy_import, "write_journal", fail_after_commit)
    error(
        "legacy_restart_required",
        lambda: service.execute("legacy.apply", {"previewId": preview["previewId"], "confirmed": True}),
    )
    assert service.restart_required
    assert [item.name for item in backend.playlists.list_summaries()] == ["My Set"]


def test_import_never_opens_audio_and_preserves_all_source_hashes(tmp_path, monkeypatch):
    import os

    source, backend, service = fixture(tmp_path)
    audio = tmp_path / "music.flac"
    audio.write_bytes(b"synthetic audio sentinel")
    digest = hashlib.sha256(audio.read_bytes()).hexdigest()
    with sqlite3.connect(source / "xfinaudio.sqlite3") as db:
        db.execute("UPDATE tracks SET path=?", (str(audio),))
    with sqlite3.connect(source / "playlists.db") as db:
        db.execute("UPDATE playlist_tracks SET track_path=?", (str(audio),))
    before = hashes(source)
    original_open = os.open

    def guarded(path, *args, **kwargs):
        assert Path(path).name != audio.name, "Importer tried to open audio"
        return original_open(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(os, "open", guarded)
        preview = service.execute("legacy.preview", {"source": str(source)})
        service.execute("legacy.apply", {"previewId": preview["previewId"], "confirmed": True})
    assert hashes(source) == before and hashlib.sha256(audio.read_bytes()).hexdigest() == digest
