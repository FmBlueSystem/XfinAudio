"""Rescan can only revisit roots already granted by explicit folder selection."""

import pytest

from tests.test_headless_backend import tagged_flac
from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.library.scan_service import ScanCancellationToken


def test_private_roots_and_rescan_update_all_existing_authorized_folders(tmp_path):
    backend = HeadlessBackend(tmp_path / "data")
    roots = [tmp_path / "first", tmp_path / "second"]
    for index, root in enumerate(roots):
        tagged_flac(root / "old.flac", index)
        backend.execute("library.scan", {"root": str(root)})
    assert backend.execute("library.roots", {}) == {"roots": [str(root) for root in roots]}
    for index, root in enumerate(roots):
        tagged_flac(root / "new.flac", index)
    before = {path: path.read_bytes() for root in roots for path in root.iterdir()}
    result = backend.execute("library.rescan", {})
    assert len(result["tracks"]) == 4 and result["cancelled"] is False
    assert all(path.read_bytes() == content for path, content in before.items())
    assert HeadlessBackend(tmp_path / "data").execute("library.roots", {}) == {"roots": [str(root) for root in roots]}


def test_cancelled_rescan_keeps_prior_records_and_invalidates_review(tmp_path):
    backend = HeadlessBackend(tmp_path / "data")
    root = tmp_path / "music"
    for index in range(3):
        tagged_flac(root / f"{index}.flac", index)
    backend.execute("library.scan", {"root": str(root)})
    backend.execute("prep.generate", {"targetTrackCount": 3})
    token = ScanCancellationToken()
    token.cancel()
    result = backend.execute("library.rescan", {}, cancellation_token=token)
    assert result["cancelled"] and len(result["tracks"]) == 3 and backend.review_id is None


def test_rescan_rejects_empty_roots_forged_paths_and_changed_ancestor(tmp_path):
    backend = HeadlessBackend(tmp_path / "data")
    with pytest.raises(BackendError):
        backend.execute("library.rescan", {})
    root = tmp_path / "parent" / "music"
    tagged_flac(root / "known.flac")
    backend.execute("library.scan", {"root": str(root)})
    with pytest.raises(BackendError):
        backend.execute("library.rescan", {"root": str(tmp_path)})
    outside = tmp_path / "outside"
    tagged_flac(outside / "music" / "ungranted.flac")
    root.parent.rename(tmp_path / "original-parent")
    root.parent.symlink_to(outside, target_is_directory=True)
    with pytest.raises(BackendError):
        backend.execute("library.rescan", {})
    assert backend.roots == [root]
    assert len(backend.execute("library.list", {})["tracks"]) == 1
