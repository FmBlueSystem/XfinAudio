"""Tests for the read-only Serato history/crate-membership spike.

The fixture tree is SYNTHETIC (see tests/fixtures/serato/README.md): its
field tags are placeholders pending verification against a sanitized live
Serato sample.
"""

import hashlib
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.fixtures.serato.serato_fixture_builder import (
    TRACK_ONE_PATH,
    TRACK_ONE_PLAYED_AT_MS,
    TRACK_TWO_PATH,
    TRACK_TWO_PLAYED_AT_MS,
    build_unknown_type_session_bytes,
    encode_typed_string,
    tlv,
)

FIXTURE_SERATO_ROOT = Path(__file__).resolve().parent / "fixtures" / "serato" / "_Serato_"


def _copy_fixture_tree(destination: Path) -> Path:
    shutil.copytree(FIXTURE_SERATO_ROOT, destination)
    return destination


def _fingerprint(root: Path) -> dict[str, tuple[int, int, str]]:
    """Content+size+mtime fingerprint of every file under root."""
    fingerprint: dict[str, tuple[int, int, str]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            info = path.stat()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            fingerprint[str(path.relative_to(root))] = (info.st_size, info.st_mtime_ns, digest)
    return fingerprint


def _session_with_timestamp_ms(played_at_ms: int) -> bytes:
    """Build a session whose only timestamp is an arbitrary 64-bit ms value."""
    track_records = [
        tlv(b"pfil", encode_typed_string(TRACK_ONE_PATH)),
        tlv(b"ptim", b"j" + played_at_ms.to_bytes(8, "big", signed=True)),
    ]
    version_record = tlv(b"vrsn", encode_typed_string("1.0/Serato DJ History"))
    session_record = tlv(b"osen", b"o" + b"".join(track_records))
    return version_record + session_record


def _session_with_nested_entries(depth: int) -> bytes:
    """Build a session with adversarially deep 'o' container nesting."""
    inner = tlv(b"leaf", encode_typed_string("leaf"))
    for _ in range(depth):
        inner = tlv(b"nest", b"o" + inner)
    version_record = tlv(b"vrsn", encode_typed_string("1.0/Serato DJ History"))
    return version_record + tlv(b"osen", b"o" + inner)


def test_read_serato_history_parses_synthetic_fixture_sessions(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_history import read_serato_history

    serato_root = _copy_fixture_tree(tmp_path / "serato")
    work_dir = tmp_path / "work"

    sessions = read_serato_history(serato_root, work_dir)

    assert [session.track_path for session in sessions] == [TRACK_ONE_PATH, TRACK_TWO_PATH]
    assert [session.title for session in sessions] == ["Track One", "Track Two"]
    assert [session.artist for session in sessions] == ["Artist One", None]
    assert sessions[0].played_at == datetime.fromtimestamp(TRACK_ONE_PLAYED_AT_MS / 1000, tz=UTC)
    assert sessions[1].played_at == datetime.fromtimestamp(TRACK_TWO_PLAYED_AT_MS / 1000, tz=UTC)
    assert sessions[0].unknown_fields == ()
    assert sessions[1].unknown_fields == ()


def test_read_serato_history_records_unknown_tags_and_types_without_error(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_history import parse_serato_history_session_bytes

    unknown_session_bytes = build_unknown_type_session_bytes()

    parsed = parse_serato_history_session_bytes(unknown_session_bytes)

    # Sanity: the known entry still decoded despite the unknown siblings.
    assert parsed.track_path == TRACK_ONE_PATH
    assert "xtrk:unknown-type:Z" in parsed.unknown_fields
    assert "osen.qnew" in parsed.unknown_fields


def test_parse_truncated_session_bytes_raises_clear_error(tmp_path: Path) -> None:
    from tests.fixtures.serato.serato_fixture_builder import build_session_bytes
    from xfinaudio.exporting.serato_history import (
        SeratoHistoryParseError,
        parse_serato_history_session_bytes,
    )

    session_bytes = build_session_bytes(
        track_path=TRACK_ONE_PATH,
        title="Track One",
        artist="Artist One",
        played_at_ms=TRACK_ONE_PLAYED_AT_MS,
    )
    truncated = session_bytes[: len(session_bytes) // 2]

    with pytest.raises(SeratoHistoryParseError):
        parse_serato_history_session_bytes(truncated)


def test_full_read_path_never_mutates_the_serato_tree(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_history import read_crate_membership, read_serato_history

    serato_root = _copy_fixture_tree(tmp_path / "serato")
    work_dir = tmp_path / "work"

    before = _fingerprint(serato_root)
    read_serato_history(serato_root, work_dir)
    read_crate_membership(serato_root, work_dir)
    after = _fingerprint(serato_root)

    assert after == before
    assert set(after) == set(before)


def test_read_path_writes_only_under_work_dir(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_history import read_crate_membership, read_serato_history

    serato_root = _copy_fixture_tree(tmp_path / "serato")
    work_dir = tmp_path / "work"

    read_serato_history(serato_root, work_dir)
    read_crate_membership(serato_root, work_dir)

    copied = {str(path.relative_to(work_dir)) for path in work_dir.rglob("*") if path.is_file()}
    assert copied == {
        "history_sessions/session_2024_01_01",
        "history_sessions/session_2024_01_02",
        "crate_copies/House.crate",
        "crate_copies/PeakTime.crate",
    }
    # Nothing new appeared inside the Serato tree either.
    assert not _fingerprint(serato_root).keys() - {
        "History/sessions/session_2024_01_01",
        "History/sessions/session_2024_01_02",
        "Subcrates/House.crate",
        "Subcrates/PeakTime.crate",
    }


def test_read_crate_membership_counts_track_occurrences_across_subcrates(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_history import read_crate_membership

    serato_root = _copy_fixture_tree(tmp_path / "serato")
    work_dir = tmp_path / "work"

    membership = read_crate_membership(serato_root, work_dir)

    assert membership == {
        TRACK_ONE_PATH: 2,  # House.crate + PeakTime.crate
        "Music/track_two.flac": 1,
        "Music/track_three.flac": 1,
    }


def test_read_serato_history_returns_empty_when_history_dir_missing(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_history import read_serato_history

    serato_root = _copy_fixture_tree(tmp_path / "serato")
    shutil.rmtree(serato_root / "History")

    assert read_serato_history(serato_root, tmp_path / "work") == []


def test_serato_history_module_has_no_write_surface() -> None:
    from xfinaudio.exporting import serato_history

    source = Path(serato_history.__file__).read_text(encoding="utf-8")

    assert "shutil.copyfile" in source  # the only sanctioned live-FS operation
    assert "open(" not in source
    assert "write_bytes" not in source
    assert "write_text" not in source
    assert ".unlink" not in source
    assert "rmtree" not in source
    assert ".remove(" not in source
    # mkdir is only allowed on the caller-owned scratch dir.
    mkdir_lines = [line for line in source.splitlines() if ".mkdir(" in line]
    assert mkdir_lines, "expected mkdir calls scoped to work_dir"
    assert all("work_dir" in line for line in mkdir_lines)


# --- D1: work_dir / live Serato tree overlap guard -------------------------


def test_read_serato_history_rejects_work_dir_equal_to_serato_root(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_history import read_serato_history

    serato_root = _copy_fixture_tree(tmp_path / "serato")

    with pytest.raises(ValueError, match="overlap"):
        read_serato_history(serato_root, serato_root)

    # The guard must fire before any mkdir/copyfile side effect.
    assert not list(serato_root.rglob("history_sessions"))


def test_read_serato_history_rejects_work_dir_nested_inside_serato_tree(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_history import read_serato_history

    serato_root = _copy_fixture_tree(tmp_path / "serato")

    with pytest.raises(ValueError, match="overlap"):
        read_serato_history(serato_root, serato_root / "History" / "work")

    assert not (serato_root / "History" / "work").exists()


def test_read_crate_membership_rejects_work_dir_nested_inside_serato_tree(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_history import read_crate_membership

    serato_root = _copy_fixture_tree(tmp_path / "serato")

    with pytest.raises(ValueError, match="overlap"):
        read_crate_membership(serato_root, serato_root / "Subcrates" / "work")

    assert not (serato_root / "Subcrates" / "work").exists()


def test_readers_reject_serato_tree_nested_inside_work_dir(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_history import read_crate_membership, read_serato_history

    serato_root = _copy_fixture_tree(tmp_path / "serato")

    # work_dir is tmp_path itself, so the Serato tree lives inside it.
    with pytest.raises(ValueError, match="overlap"):
        read_serato_history(serato_root, tmp_path)
    with pytest.raises(ValueError, match="overlap"):
        read_crate_membership(serato_root, tmp_path)


def test_sibling_work_dir_still_reads_sessions_and_crates(tmp_path: Path) -> None:
    from xfinaudio.exporting.serato_history import read_crate_membership, read_serato_history

    serato_root = _copy_fixture_tree(tmp_path / "serato")
    work_dir = tmp_path / "work"  # sibling of the Serato tree: must keep working

    sessions = read_serato_history(serato_root, work_dir)
    membership = read_crate_membership(serato_root, work_dir)

    assert len(sessions) == 2
    assert membership


# --- D2: bounded recursion on deeply nested 'o' records --------------------


def test_deeply_nested_session_records_do_not_hit_recursion_limit() -> None:
    from xfinaudio.exporting.serato_history import parse_serato_history_session_bytes

    session_bytes = _session_with_nested_entries(depth=1500)

    parsed = parse_serato_history_session_bytes(session_bytes)  # must not raise RecursionError

    assert any(field.endswith(":max-nesting-depth") for field in parsed.unknown_fields)


# --- D3: out-of-range 'j' timestamps raise the parse-error contract --------


@pytest.mark.parametrize(
    ("label", "played_at_ms"),
    [
        ("int63-max", 2**63 - 1),
        ("int64-min", -(2**63)),
        ("year-10000", 253_402_301_000_000),  # beyond datetime.max (9999-12-31)
    ],
)
def test_out_of_range_timestamp_raises_serato_parse_error(label: str, played_at_ms: int) -> None:
    from xfinaudio.exporting.serato_history import (
        SeratoHistoryParseError,
        parse_serato_history_session_bytes,
    )

    with pytest.raises(SeratoHistoryParseError, match="timestamp"):
        parse_serato_history_session_bytes(_session_with_timestamp_ms(played_at_ms))
