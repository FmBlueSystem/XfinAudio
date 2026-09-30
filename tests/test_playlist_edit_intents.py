"""Offline edit proposals must be deterministic and constraint-safe."""

import pytest

from xfinaudio.application.playlist_edit_intents import propose_edit, validate_edit
from xfinaudio.library.models import TrackRecord


def records():
    return [TrackRecord(path=p, energy_level=e, duration=180) for p, e in (("a", 5), ("b", 2), ("c", 8))]


def test_shortening_retains_locked_tail_and_source_order():
    assert propose_edit("shorten to 2 tracks", ["a", "b", "c"], records(), locked_paths={"c"}) == ("a", "c")


def test_spanish_duration_request_removes_unlocked_tail():
    assert propose_edit("acorta a 6 minutos", ["a", "b", "c"], records()) == ("a", "b")


def test_energy_ramp_preserves_locked_slot_and_exclusions():
    assert propose_edit("raise energy", ["a", "b", "c"], records(), locked_paths={"a"}) == ("a", "b", "c")
    assert propose_edit("baja la energía", ["a", "b", "c"], records(), excluded_paths={"b"}) == ("c", "a")


@pytest.mark.parametrize("phrase", ["delete everything", "do not shorten to 2 tracks", "shorten to 0 tracks"])
def test_unsupported_or_invalid_request_is_rejected(phrase):
    with pytest.raises(ValueError):
        propose_edit(phrase, ["a", "b", "c"], records())


def test_missing_metadata_is_not_invented():
    with pytest.raises(ValueError, match="energy"):
        propose_edit("raise energy", ["a"], [TrackRecord(path="a")])
    with pytest.raises(ValueError, match="duration"):
        propose_edit("shorten to 5 minutes", ["a"], [TrackRecord(path="a")])


def test_impossible_lock_constraints_are_rejected():
    with pytest.raises(ValueError, match="locked"):
        propose_edit("shorten to 1 track", ["a", "b", "c"], records(), locked_paths={"a", "c"})
    with pytest.raises(ValueError, match="locked"):
        propose_edit("shorten to 2 tracks", ["a", "b", "c"], records(), locked_paths={"a"}, excluded_paths={"a"})


@pytest.mark.parametrize("candidate", [("a", "x"), ("a", "a"), ("b",)])
def test_validator_rejects_additions_duplicates_and_removed_locks(candidate):
    with pytest.raises(ValueError):
        validate_edit(("a", "b"), candidate, locked_paths={"a"})


def test_validator_rejects_exclusions():
    with pytest.raises(ValueError, match="excluded"):
        validate_edit(("a", "b"), ("a", "b"), excluded_paths={"b"})
