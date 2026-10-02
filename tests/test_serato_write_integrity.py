"""Writer safety tests use only synthetic temporary crate files."""

import os
from pathlib import Path

import pytest

from xfinaudio.exporting import serato_crate as crate


@pytest.mark.parametrize("case", ["malformed", "mismatch", "unsafe", "nul"])
def test_invalid_payload_rejected_before_filesystem_changes(tmp_path, case):
    plan = crate.plan_serato_crate_export("Test", ["Music/A.flac"], tmp_path)
    updates = {"crate_bytes": b"broken"}
    if case == "mismatch":
        updates = {"crate_bytes": crate.build_serato_crate_bytes(["Music/B.flac"])}
    elif case in {"unsafe", "nul"}:
        path = "../escape.flac" if case == "unsafe" else "Music/\0A.flac"
        updates = {
            "relative_paths": (path,),
            "crate_bytes": plan.crate_bytes.replace("Music/A.flac".encode("utf-16-be"), path.encode("utf-16-be")),
        }
    with pytest.raises(OSError, match="payload"):
        crate.write_serato_crate(plan.model_copy(update=updates), confirm=True)
    assert not plan.target_path.parent.exists()


@pytest.mark.parametrize("dangling", [False, True])
def test_final_symlink_is_rejected_without_touching_referent(tmp_path, dangling):
    plan = crate.plan_serato_crate_export("Test", [], tmp_path)
    plan.target_path.parent.mkdir(parents=True)
    victim = tmp_path / "victim"
    if not dangling:
        victim.write_bytes(b"untouched")
    plan.target_path.symlink_to(victim)
    with pytest.raises(OSError, match="symlink"):
        crate.write_serato_crate(plan, confirm=True)
    assert plan.target_path.is_symlink()
    assert not victim.exists() if dangling else victim.read_bytes() == b"untouched"


def test_backups_are_exclusive_and_preserve_existing_symlink_and_history(tmp_path):
    plan = crate.plan_serato_crate_export("Test", [], tmp_path)
    plan.target_path.parent.mkdir(parents=True)
    victim = tmp_path / "victim"
    victim.write_bytes(b"untouched")
    plan.backup_path.symlink_to(victim)
    backups = []
    for value in (b"first", b"second"):
        plan.target_path.write_bytes(value)
        result = crate.write_serato_crate(plan, confirm=True)
        assert result.backup_path is not None
        backups.append(result.backup_path)
        assert result.backup_path.read_bytes() == value
    assert backups[0] != backups[1]
    assert backups[0].read_bytes() == b"first"
    assert victim.read_bytes() == b"untouched"
    assert plan.backup_path.is_symlink()


def test_publication_uses_complete_same_directory_atomic_replacement(tmp_path, monkeypatch):
    plan = crate.plan_serato_crate_export("Test", [], tmp_path)
    plan.target_path.parent.mkdir(parents=True)
    plan.target_path.write_bytes(b"previous")
    calls = []
    original = os.replace

    def replace(source, target):
        assert Path(source).parent == plan.target_path.parent
        assert Path(source).read_bytes() == plan.crate_bytes
        assert Path(target).read_bytes() == b"previous"
        calls.append(target)
        original(source, target)

    monkeypatch.setattr(os, "replace", replace)
    crate.write_serato_crate(plan, confirm=True)
    assert calls == [plan.target_path]


@pytest.mark.parametrize("existing", [False, True])
def test_readback_failure_recovers_and_raises_typed_error(tmp_path, monkeypatch, existing):
    plan = crate.plan_serato_crate_export("Test", [], tmp_path)
    if existing:
        plan.target_path.parent.mkdir(parents=True)
        plan.target_path.write_bytes(b"previous")
    monkeypatch.setattr(crate, "validate_serato_crate_file", lambda plan: False)
    with pytest.raises(OSError, match="readback.*recovered") as error:
        crate.write_serato_crate(plan, confirm=True)
    assert type(error.value).__name__ == "SeratoCrateWriteError"
    assert plan.target_path.read_bytes() == b"previous" if existing else not plan.target_path.exists()
    assert not list(plan.target_path.parent.glob("*.tmp"))


def test_failed_readback_preserves_concurrently_replaced_target(tmp_path, monkeypatch):
    plan = crate.plan_serato_crate_export("Test", [], tmp_path)

    def replace_during_validation(plan):
        other = tmp_path / "other"
        other.write_bytes(b"concurrent")
        os.replace(other, plan.target_path)
        return False

    monkeypatch.setattr(crate, "validate_serato_crate_file", replace_during_validation)
    with pytest.raises(OSError, match="manual recovery"):
        crate.write_serato_crate(plan, confirm=True)
    assert plan.target_path.read_bytes() == b"concurrent"


@pytest.mark.parametrize("link_target", ["written_path", "backup_path"])
def test_rollback_rejects_symlinks(tmp_path, link_target):
    plan = crate.plan_serato_crate_export("Test", [], tmp_path)
    plan.target_path.parent.mkdir(parents=True)
    plan.target_path.write_bytes(b"previous")
    result = crate.write_serato_crate(plan, confirm=True)
    victim = tmp_path / "victim"
    victim.write_bytes(b"untouched")
    path = getattr(result, link_target)
    path.unlink()
    path.symlink_to(victim)
    with pytest.raises(OSError, match="symlink"):
        crate.rollback_serato_crate_write(result)
    assert victim.read_bytes() == b"untouched"


def test_publication_error_leaves_original_and_backup_intact(tmp_path, monkeypatch):
    plan = crate.plan_serato_crate_export("Test", [], tmp_path)
    plan.target_path.parent.mkdir(parents=True)
    plan.target_path.write_bytes(b"previous")

    def fail_replace(source, target):
        raise OSError("synthetic disk failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="Serato write failed"):
        crate.write_serato_crate(plan, confirm=True)
    assert plan.target_path.read_bytes() == b"previous"
    assert plan.backup_path.read_bytes() == b"previous"
    assert not list(plan.target_path.parent.glob("*.tmp"))


def test_readback_exception_also_recovers(tmp_path, monkeypatch):
    plan = crate.plan_serato_crate_export("Test", [], tmp_path)

    def fail_readback(plan):
        raise PermissionError("synthetic read denial")

    monkeypatch.setattr(crate, "validate_serato_crate_file", fail_readback)
    with pytest.raises(OSError, match="readback.*recovered"):
        crate.write_serato_crate(plan, confirm=True)
    assert not plan.target_path.exists()
