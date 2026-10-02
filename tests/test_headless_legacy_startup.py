"""Canonical startup fails before opening app data behind a symlink alias."""

from pathlib import Path

import pytest

from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError


@pytest.mark.parametrize("ancestor_alias", [False, True])
def test_aliased_startup_rejects_before_any_target_mutation(tmp_path: Path, ancestor_alias: bool):
    target = tmp_path / "real"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    if ancestor_alias:
        target = target / "profile"
        target.mkdir()
        alias = alias / "profile"
    sentinel = target / "sentinel.bin"
    sentinel.write_bytes(b"original application sentinel")
    before = {item.name: item.read_bytes() for item in target.iterdir()}

    with pytest.raises(BackendError) as caught:
        HeadlessBackend(alias)

    assert caught.value.code == "legacy_invalid"
    assert {item.name: item.read_bytes() for item in target.iterdir()} == before
    assert not (target / "tracks.db").exists()
    assert not (target / "playlists.db").exists()
    assert not (target / "roots.json").exists()
    assert not (target / "settings.json").exists()
    assert not (target / ".legacy-import-journal.json").exists()
