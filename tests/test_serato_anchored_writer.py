"""Descriptor-bound writer tests use disposable fake Serato directories only."""

import os
from contextlib import contextmanager

import pytest

from xfinaudio.exporting import serato_crate as crate


@contextmanager
def anchored_plan(tmp_path, previous=None):
    plan = crate.plan_serato_crate_export("Test", ["Music/A.flac"], tmp_path)
    plan.target_path.parent.mkdir(parents=True)
    if previous is not None:
        plan.target_path.write_bytes(previous)
    descriptor = os.open(plan.target_path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        yield plan, descriptor
    finally:
        os.close(descriptor)


def identity(path):
    info = path.stat()
    return info.st_dev, info.st_ino, info.st_mtime_ns, info.st_size


def test_anchored_write_requires_explicit_preview_target_identity(tmp_path):
    with anchored_plan(tmp_path) as (plan, descriptor):
        with pytest.raises(crate.SeratoCrateWriteError, match="identity"):
            crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor)
        assert list(plan.target_path.parent.iterdir()) == []


@pytest.mark.parametrize("previous", [None, b"previous"])
def test_fixed_target_identity_rejects_preview_changes_before_backup(tmp_path, previous):
    with anchored_plan(tmp_path, previous) as (plan, descriptor):
        expected = identity(plan.target_path) if previous is not None else None
        plan.target_path.write_bytes(b"changed since preview")
        with pytest.raises(crate.SeratoCrateWriteError, match="changed"):
            crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor, expected_target_identity=expected)
        assert plan.target_path.read_bytes() == b"changed since preview"
        assert not plan.backup_path.exists()


def test_anchored_backup_collision_does_not_choose_unapproved_filename(tmp_path):
    with anchored_plan(tmp_path, b"previous") as (plan, descriptor):
        plan.backup_path.write_bytes(b"older backup")
        with pytest.raises(crate.SeratoCrateWriteError):
            crate.write_serato_crate(
                plan, confirm=True, directory_fd=descriptor, expected_target_identity=identity(plan.target_path)
            )
        assert plan.target_path.read_bytes() == b"previous"
        assert plan.backup_path.read_bytes() == b"older backup"
        assert len(list(plan.target_path.parent.iterdir())) == 2


@pytest.mark.parametrize("previous", [None, b"previous"])
def test_anchored_write_validation_and_rollback_ignore_swapped_parent(tmp_path, previous):
    with anchored_plan(tmp_path, previous) as (plan, descriptor):
        expected = identity(plan.target_path) if previous is not None else None
        original = plan.target_path.parent.with_name("original")
        plan.target_path.parent.rename(original)
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        victim = elsewhere / plan.target_path.name
        victim.write_bytes(b"untouched")
        plan.target_path.parent.symlink_to(elsewhere, target_is_directory=True)
        result = crate.write_serato_crate(
            plan, confirm=True, directory_fd=descriptor, expected_target_identity=expected
        )
        assert (original / plan.target_path.name).read_bytes() == plan.crate_bytes
        assert crate.validate_serato_crate_file(plan, directory_fd=descriptor)
        crate.rollback_serato_crate_write(result, directory_fd=descriptor)
        assert victim.read_bytes() == b"untouched"
        target = original / plan.target_path.name
        assert target.read_bytes() == previous if previous is not None else not target.exists()
        assert not list(original.glob(".*.tmp"))
        assert len(list(elsewhere.iterdir())) == 1


@pytest.mark.parametrize("phase", [1, 2, 3])
@pytest.mark.parametrize("previous", [None, b"previous"])
def test_guard_runs_before_side_effects_before_publication_and_after_readback(tmp_path, phase, previous):
    with anchored_plan(tmp_path, previous) as (plan, descriptor):
        expected = identity(plan.target_path) if previous is not None else None
        calls = 0

        def guard():
            nonlocal calls
            calls += 1
            if calls == phase:
                if phase == 1:
                    assert not plan.backup_path.exists()
                if phase < 3:
                    assert (
                        plan.target_path.read_bytes() == previous
                        if previous is not None
                        else not plan.target_path.exists()
                    )
                else:
                    assert plan.target_path.read_bytes() == plan.crate_bytes
                raise ValueError("source or destination changed")

        with pytest.raises(crate.SeratoCrateWriteError):
            crate.write_serato_crate(
                plan, confirm=True, directory_fd=descriptor, expected_target_identity=expected, guard=guard
            )
        assert calls == phase
        assert plan.target_path.read_bytes() == previous if previous is not None else not plan.target_path.exists()
        assert not list(plan.target_path.parent.glob(".*.tmp"))


def test_target_swapped_by_final_guard_is_not_overwritten(tmp_path):
    with anchored_plan(tmp_path) as (plan, descriptor):
        calls = 0

        def guard():
            nonlocal calls
            calls += 1
            if calls == 2:
                plan.target_path.write_bytes(b"concurrent")

        with pytest.raises(crate.SeratoCrateWriteError, match="changed"):
            crate.write_serato_crate(
                plan, confirm=True, directory_fd=descriptor, expected_target_identity=None, guard=guard
            )
        assert plan.target_path.read_bytes() == b"concurrent"


@pytest.mark.parametrize("leaf", ["target", "backup"])
def test_anchored_writer_rejects_leaf_symlinks(tmp_path, leaf):
    with anchored_plan(tmp_path, b"previous") as (plan, descriptor):
        expected = identity(plan.target_path)
        victim = tmp_path / "victim"
        victim.write_bytes(b"untouched")
        if leaf == "target":
            plan.target_path.unlink()
            plan.target_path.symlink_to(victim)
        else:
            plan.backup_path.symlink_to(victim)
        with pytest.raises(crate.SeratoCrateWriteError):
            crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor, expected_target_identity=expected)
        assert victim.read_bytes() == b"untouched"


def test_anchored_readback_failure_recovers_original_directory_after_parent_swap(tmp_path, monkeypatch):
    with anchored_plan(tmp_path, b"previous") as (plan, descriptor):
        expected = identity(plan.target_path)
        original = plan.target_path.parent.with_name("original")
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        victim = elsewhere / plan.target_path.name
        victim.write_bytes(b"untouched")

        def failed_validation(plan, *, directory_fd):
            assert directory_fd == descriptor
            plan.target_path.parent.rename(original)
            plan.target_path.parent.symlink_to(elsewhere, target_is_directory=True)
            return False

        monkeypatch.setattr(crate, "validate_serato_crate_file", failed_validation)
        with pytest.raises(crate.SeratoCrateWriteError, match="recovered"):
            crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor, expected_target_identity=expected)
        assert (original / plan.target_path.name).read_bytes() == b"previous"
        assert victim.read_bytes() == b"untouched"


def test_anchored_rollback_preserves_changed_target(tmp_path):
    with anchored_plan(tmp_path) as (plan, descriptor):
        result = crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor, expected_target_identity=None)
        expected = identity(plan.target_path)
        plan.target_path.write_bytes(b"concurrent")
        with pytest.raises(crate.SeratoCrateWriteError, match="changed"):
            crate.rollback_serato_crate_write(result, directory_fd=descriptor, expected_target_identity=expected)
        assert plan.target_path.read_bytes() == b"concurrent"


def test_target_change_after_readback_is_not_reported_as_success(tmp_path):
    with anchored_plan(tmp_path) as (plan, descriptor):
        calls = 0

        def guard():
            nonlocal calls
            calls += 1
            if calls == 3:
                plan.target_path.write_bytes(b"concurrent")

        with pytest.raises(crate.SeratoCrateWriteError, match="manual recovery"):
            crate.write_serato_crate(
                plan, confirm=True, directory_fd=descriptor, expected_target_identity=None, guard=guard
            )
        assert plan.target_path.read_bytes() == b"concurrent"


def test_default_atomic_replace_seam_keeps_legacy_call_shape(tmp_path, monkeypatch):
    plan = crate.plan_serato_crate_export("Test", [], tmp_path)
    original = crate._atomic_replace

    def replace(target, data, expected):
        return original(target, data, expected)

    monkeypatch.setattr(crate, "_atomic_replace", replace)
    assert crate.write_serato_crate(plan, confirm=True).validated


def test_expected_absent_publication_never_clobbers_a_last_instant_arrival(tmp_path, monkeypatch):
    with anchored_plan(tmp_path) as (plan, descriptor):
        original = crate._file_identity
        checks = 0

        def checked_identity(path, *, directory_fd=None):
            nonlocal checks
            observed = original(path, directory_fd=directory_fd)
            checks += 1
            if checks == 3:
                plan.target_path.write_bytes(b"concurrent")
            return observed

        monkeypatch.setattr(crate, "_file_identity", checked_identity)
        with pytest.raises(crate.SeratoCrateWriteError):
            crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor, expected_target_identity=None)
        assert plan.target_path.read_bytes() == b"concurrent"
        assert not list(plan.target_path.parent.glob(".*.tmp"))


def test_new_crate_uses_exclusive_rename_without_requiring_hardlinks(tmp_path, monkeypatch):
    def unsupported(*args, **kwargs):
        raise OSError("Filesystem does not support hard links")

    monkeypatch.setattr(crate.os, "link", unsupported)
    with anchored_plan(tmp_path) as (plan, descriptor):
        result = crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor, expected_target_identity=None)
        assert result.validated and plan.target_path.read_bytes() == plan.crate_bytes


@pytest.mark.parametrize("platform,symbol,flag", [("darwin", "renameatx_np", 4), ("linux", "renameat2", 1)])
def test_native_exclusive_rename_uses_documented_platform_abi(monkeypatch, platform, symbol, flag):
    calls = []

    class Function:
        def __call__(self, *args):
            calls.append(args)
            return 0

    function = Function()

    class Library:
        pass

    library = Library()
    setattr(library, symbol, function)
    monkeypatch.setattr(crate.sys, "platform", platform)
    monkeypatch.setattr(crate.ctypes, "CDLL", lambda name, **kwargs: library)
    assert crate._exclusive_rename("pending", "crate", 23)
    assert calls == [(23, b"pending", 23, b"crate", flag)]
    assert function.restype == crate.ctypes.c_int
    assert len(function.argtypes) == 5


@pytest.mark.parametrize("failure", [crate.errno.EEXIST, crate.errno.EACCES, crate.errno.ENOSPC])
def test_native_exclusive_rename_does_not_retry_real_errors(monkeypatch, failure):
    class Function:
        def __call__(self, *args):
            crate.ctypes.set_errno(failure)
            return -1

    class Library:
        renameat2 = Function()

    monkeypatch.setattr(crate.sys, "platform", "linux")
    monkeypatch.setattr(crate.ctypes, "CDLL", lambda name, **kwargs: Library())
    monkeypatch.setattr(crate.os, "link", lambda *args, **kwargs: pytest.fail("Must not fallback on real failures"))
    with pytest.raises(OSError) as error:
        crate._publish_exclusive("pending", "crate", 23)
    assert error.value.errno == failure


def test_unsupported_native_rename_uses_safe_link_fallback(tmp_path, monkeypatch):
    class Function:
        def __call__(self, *args):
            crate.ctypes.set_errno(crate.errno.ENOTSUP)
            return -1

    class Library:
        renameat2 = Function()

    monkeypatch.setattr(crate.sys, "platform", "linux")
    monkeypatch.setattr(crate.ctypes, "CDLL", lambda name, **kwargs: Library())
    with anchored_plan(tmp_path) as (plan, descriptor):
        result = crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor, expected_target_identity=None)
        assert result.validated


def test_both_exclusive_primitives_unsupported_fail_without_publication(tmp_path, monkeypatch):
    monkeypatch.setattr(crate, "_exclusive_rename", lambda *args: False)

    def unsupported(*args, **kwargs):
        raise OSError(crate.errno.ENOTSUP, "Unsupported filesystem")

    monkeypatch.setattr(crate.os, "link", unsupported)
    with anchored_plan(tmp_path) as (plan, descriptor):
        with pytest.raises(crate.SeratoCrateWriteError):
            crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor, expected_target_identity=None)
        assert not list(plan.target_path.parent.iterdir())


@pytest.mark.parametrize("same_inode", [False, True])
def test_existing_target_last_instant_replacement_is_preserved(tmp_path, monkeypatch, same_inode):
    import inspect

    with anchored_plan(tmp_path, b"approved previous") as (plan, descriptor):
        expected = identity(plan.target_path)
        original = crate._file_identity
        injected = False

        def checked_identity(path, *, directory_fd=None):
            nonlocal injected
            observed = original(path, directory_fd=directory_fd)
            caller = inspect.currentframe().f_back.f_code.co_name
            if not injected and path == plan.target_path and caller == "_atomic_replace":
                injected = True
                before = plan.target_path.stat()
                if not same_inode:
                    plan.target_path.unlink()
                plan.target_path.write_bytes(b"concurrent writer")
                if same_inode:
                    os.utime(plan.target_path, ns=(before.st_atime_ns, before.st_mtime_ns))
            return observed

        monkeypatch.setattr(crate, "_file_identity", checked_identity)
        with pytest.raises(crate.SeratoCrateWriteError):
            crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor, expected_target_identity=expected)
        assert injected
        assert plan.target_path.read_bytes() == b"concurrent writer"
        assert plan.backup_path.read_bytes() == b"approved previous"


def test_successful_bound_overwrite_removes_private_recovery_name(tmp_path):
    with anchored_plan(tmp_path, b"previous") as (plan, descriptor):
        result = crate.write_serato_crate(
            plan, confirm=True, directory_fd=descriptor, expected_target_identity=identity(plan.target_path)
        )
        assert result.validated
        assert sorted(path.name for path in plan.target_path.parent.iterdir()) == ["Test.crate", "Test.crate.bak"]


def test_arrival_during_bound_overwrite_keeps_competitor_and_recovery(tmp_path, monkeypatch):
    with anchored_plan(tmp_path, b"approved previous") as (plan, descriptor):
        expected = identity(plan.target_path)
        original = crate._publish_exclusive
        arrived = False

        def publish(source, target, directory_fd):
            nonlocal arrived
            if not arrived and source.startswith(".xfinaudio-") and target == plan.target_path.name:
                arrived = True
                plan.target_path.write_bytes(b"concurrent arrival")
            return original(source, target, directory_fd)

        monkeypatch.setattr(crate, "_publish_exclusive", publish)
        with pytest.raises(crate.SeratoCrateWriteError, match="manual recovery"):
            crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor, expected_target_identity=expected)
        assert plan.target_path.read_bytes() == b"concurrent arrival"
        assert plan.backup_path.read_bytes() == b"approved previous"
        retained = list(plan.target_path.parent.glob(".xfinaudio-recovery-*"))
        assert len(retained) == 1 and retained[0].read_bytes() == b"approved previous"


def test_bound_preview_digest_is_checked_before_backup(tmp_path):
    import hashlib

    with anchored_plan(tmp_path, b"approved previous") as (plan, descriptor):
        before = plan.target_path.stat()
        expected = identity(plan.target_path)
        plan.target_path.write_bytes(b"concurrent writer")
        os.utime(plan.target_path, ns=(before.st_atime_ns, before.st_mtime_ns))
        with pytest.raises(crate.SeratoCrateWriteError):
            crate.write_serato_crate(
                plan,
                confirm=True,
                directory_fd=descriptor,
                expected_target_identity=expected,
                expected_target_digest=hashlib.sha256(b"approved previous").hexdigest(),
            )
        assert not plan.backup_path.exists()
        assert plan.target_path.read_bytes() == b"concurrent writer"


def test_anchored_writer_rejects_oversized_existing_crate_before_backup(tmp_path):
    with anchored_plan(tmp_path, b"old") as (plan, descriptor):
        with plan.target_path.open("r+b") as handle:
            handle.truncate(16 * 1024 * 1024 + 1)
        expected = identity(plan.target_path)
        with pytest.raises(crate.SeratoCrateWriteError, match="limit"):
            crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor, expected_target_identity=expected)
        assert identity(plan.target_path) == expected
        assert not plan.backup_path.exists()


def test_anchored_generated_payload_has_a_byte_limit(tmp_path, monkeypatch):
    with anchored_plan(tmp_path) as (plan, descriptor):
        monkeypatch.setattr(crate, "MAX_ANCHORED_CRATE_BYTES", 1)
        with pytest.raises(crate.SeratoCrateWriteError, match="limit"):
            crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor, expected_target_identity=None)
        assert not plan.target_path.exists()


def test_anchored_rollback_removal_preserves_arrival_after_last_identity_check(tmp_path, monkeypatch):
    with anchored_plan(tmp_path) as (plan, descriptor):
        original_identity = crate._file_identity
        checking_removal = False
        injected = False

        def failed_readback(*args, **kwargs):
            nonlocal checking_removal
            checking_removal = True
            return False

        def changed_after_check(path, **kwargs):
            nonlocal injected
            result = original_identity(path, **kwargs)
            if checking_removal and path == plan.target_path and not injected:
                injected = True
                arrival = path.with_name("arrival.fixture")
                arrival.write_bytes(b"concurrent arrival")
                arrival.replace(path)
            return result

        monkeypatch.setattr(crate, "validate_serato_crate_file", failed_readback)
        monkeypatch.setattr(crate, "_file_identity", changed_after_check)
        with pytest.raises(crate.SeratoCrateWriteError):
            crate.write_serato_crate(plan, confirm=True, directory_fd=descriptor, expected_target_identity=None)
        assert injected
        assert plan.target_path.read_bytes() == b"concurrent arrival"
