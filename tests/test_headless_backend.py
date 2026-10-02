"""Qt-free slice integration tests; runnable with pytest --noconftest."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from mutagen.flac import FLAC

from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.library.scan_service import ScanCancellationToken


def tagged_flac(path: Path, index: int = 0) -> None:
    """A metadata-only FLAC fixture, never used as a playback fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    streaminfo = b"\x10\x00\x10\x00" + bytes(6)
    streaminfo += ((44100 << 44) | (1 << 41) | (15 << 36) | (44100 * 240)).to_bytes(8, "big")
    path.write_bytes(b"fLaC\x80\x00\x00\x22" + streaminfo + bytes(16))
    tags = FLAC(path)
    tags["title"] = f"Track {index}"
    tags["artist"] = "Test Artist"
    tags["bpm"] = str(120 + index)
    tags["initialkey"] = "8A"
    tags["energylevel"] = "5"
    tags["genre"] = "House"
    tags.save()


def test_scan_generate_save_reopen_without_audio_mutation(tmp_path: Path) -> None:
    root = tmp_path / "music"
    for index in range(3):
        tagged_flac(root / f"{index}.flac", index)
    before = {p: hashlib.sha256(p.read_bytes()).digest() for p in root.iterdir()}
    backend = HeadlessBackend(tmp_path / "data")
    progress: list[dict] = []
    result = backend.execute("library.scan", {"root": str(root)}, progress=progress.append)
    assert len(result["tracks"]) == result["completeCount"] == 3
    assert result["incompleteCount"] == 0
    assert progress[-1]["processedCount"] == 3
    assert str(root) not in json.dumps(result)
    review = backend.execute("prep.generate", {"targetTrackCount": 3})
    assert review["variant"] == "balanced"
    assert len(review["tracks"]) == 3
    assert review["blockers"] == []
    saved = backend.execute("playlist.save", {"name": "First set", "reviewId": review["reviewId"]})
    restored = HeadlessBackend(tmp_path / "data")
    assert restored.execute("playlist.list", {})["playlists"][0]["id"] == saved["id"]
    opened = restored.execute("playlist.open", {"playlistId": saved["id"]})
    assert [track["id"] for track in opened["tracks"]] == [track["id"] for track in review["tracks"]]
    assert restored.execute("track.resolve", {"trackId": opened["tracks"][0]["id"]})["path"] in map(str, before)
    assert all(hashlib.sha256(p.read_bytes()).digest() == digest for p, digest in before.items())


def test_symlinks_cannot_import_or_resolve_outside_authorized_root(tmp_path: Path) -> None:
    root = tmp_path / "music"
    tagged_flac(root / "safe.flac")
    outside = tmp_path / "outside.flac"
    tagged_flac(outside)
    (root / "escape.flac").symlink_to(outside)
    backend = HeadlessBackend(tmp_path / "data")
    tracks = backend.execute("library.scan", {"root": str(root)})["tracks"]
    assert len(tracks) == 1
    (root / "safe.flac").unlink()
    (root / "safe.flac").symlink_to(outside)
    with pytest.raises(BackendError, match="authorized"):
        backend.execute("track.resolve", {"trackId": tracks[0]["id"]})


def test_cancel_keeps_committed_library_and_invalidates_review(tmp_path: Path) -> None:
    root = tmp_path / "music"
    tagged_flac(root / "safe.flac")
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    token = ScanCancellationToken()
    token.cancel()
    result = backend.execute("library.scan", {"root": str(root)}, cancellation_token=token)
    assert result["cancelled"] is True
    assert len(backend.execute("library.list", {})["tracks"]) == 1
    with pytest.raises(BackendError, match="review"):
        backend.execute("playlist.save", {"name": "Stale", "reviewId": "old"})


@pytest.mark.parametrize(
    "method,params",
    [
        ("library.scan", {"root": ""}),
        ("library.scan", {"root": "."}),
        ("prep.generate", {"targetTrackCount": True}),
        ("prep.generate", {"targetTrackCount": 101}),
        ("playlist.open", {"playlistId": True}),
        ("track.resolve", {"trackId": "../secret"}),
        ("unknown", {}),
        ("library.list", {"unexpected": True}),
    ],
)
def test_untrusted_parameters_fail_closed(tmp_path: Path, method: str, params: dict) -> None:
    with pytest.raises(BackendError):
        HeadlessBackend(tmp_path / "data").execute(method, params)


def test_import_and_startup_do_not_import_qt_or_desktop(tmp_path: Path) -> None:
    script = """
import importlib.abc, sys
class BlockQt(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('PySide6', 'xfinaudio.desktop', 'xfinaudio.ai')):
            raise AssertionError(fullname)
sys.meta_path.insert(0, BlockQt())
from xfinaudio.headless.backend import HeadlessBackend
assert HeadlessBackend(sys.argv[1]).execute('library.list', {})['tracks'] == []
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
    )
    assert completed.returncode == 0, completed.stderr


def test_cancelled_scan_keeps_incremental_batches_without_pruning(tmp_path: Path) -> None:
    root = tmp_path / "music"
    tagged_flac(root / "previous.flac")
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    (root / "previous.flac").unlink()
    for index in range(202):
        tagged_flac(root / f"{index:03}.flac", index % 3)
    token = ScanCancellationToken()

    def cancel_after_flush(progress: dict) -> None:
        if progress["processedCount"] == 201:
            token.cancel()

    result = backend.execute("library.scan", {"root": str(root)}, cancellation_token=token, progress=cancel_after_flush)
    assert result["cancelled"] is True
    assert len(result["tracks"]) == 201  # 200 committed new rows plus the existing row.
    assert len(HeadlessBackend(tmp_path / "data").execute("library.list", {})["tracks"]) == 201


def test_scan_preserves_exact_folder_name_with_trailing_space(tmp_path: Path) -> None:
    root = tmp_path / "music "
    tagged_flac(root / "track.flac")
    backend = HeadlessBackend(tmp_path / "data")
    assert len(backend.execute("library.scan", {"root": str(root)})["tracks"]) == 1


def test_scan_never_requests_spectral_or_loudness_analysis(tmp_path: Path, monkeypatch) -> None:
    import xfinaudio.library.scan_service as scanner

    def forbidden(*args, **kwargs):
        raise AssertionError("Audio analysis is outside this metadata-only slice")

    monkeypatch.setattr(scanner, "analyze_paths", forbidden)
    monkeypatch.setattr(scanner.LibrosaSpectralAnalyzer, "analyze", forbidden)
    root = tmp_path / "music"
    tagged_flac(root / "track.flac")
    assert HeadlessBackend(tmp_path / "data").execute("library.scan", {"root": str(root)})["completeCount"] == 1


def test_preview_resolution_returns_current_file_identity(tmp_path: Path) -> None:
    root = tmp_path / "music"
    path = root / "track.flac"
    tagged_flac(path)
    backend = HeadlessBackend(tmp_path / "data")
    track = backend.execute("library.scan", {"root": str(root)})["tracks"][0]
    resolved = backend.execute("track.resolve", {"trackId": track["id"]})
    stat = path.stat()
    assert resolved["identity"] == {
        "device": str(stat.st_dev),
        "inode": str(stat.st_ino),
        "size": str(stat.st_size),
        "mtimeNs": str(stat.st_mtime_ns),
    }


def test_preview_uses_immutable_identity_snapshot_without_database_reads(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "music"
    tagged_flac(root / "track.flac")
    backend = HeadlessBackend(tmp_path / "data")
    track = backend.execute("library.scan", {"root": str(root)})["tracks"][0]

    def forbidden():
        raise AssertionError("Preview must not block cancellation on a full library database read")

    monkeypatch.setattr(backend.repository, "list_display_tracks", forbidden)
    assert backend.execute("track.resolve", {"trackId": track["id"]})["mime"] == "audio/flac"
