import pytest

from xfinaudio.exporting.serato_crate import (
    SERATO_CRATE_VERSION,
    SeratoCrateParseError,
    SeratoExportPlan,
    build_serato_crate_bytes,
    parse_serato_crate_bytes,
    plan_serato_crate_export,
    rollback_serato_crate_write,
    validate_serato_crate_bytes,
    validate_serato_crate_file,
    write_serato_crate,
)


def tlv(tag: bytes, payload: bytes) -> bytes:
    return tag + len(payload).to_bytes(4, "big") + payload


def utf16be(value: str) -> bytes:
    return value.encode("utf-16-be")


def test_build_serato_crate_bytes_encodes_vrsn_and_ordered_otrk_ptrk_records() -> None:
    crate_bytes = build_serato_crate_bytes(["Music/A.flac", "Music/B.flac"])

    assert crate_bytes.startswith(tlv(b"vrsn", "1.0/Serato ScratchLive Crate".encode("utf-16-be")))
    first_track = tlv(b"otrk", tlv(b"ptrk", "Music/A.flac".encode("utf-16-be")))
    second_track = tlv(b"otrk", tlv(b"ptrk", "Music/B.flac".encode("utf-16-be")))
    assert crate_bytes == tlv(b"vrsn", "1.0/Serato ScratchLive Crate".encode("utf-16-be")) + first_track + second_track


@pytest.mark.parametrize(
    "bad_path",
    ["", "/absolute.flac", "../escape.flac", "Music/../escape.flac", "C:/Music/A.flac", "C:\\Music\\A.flac"],
)
def test_build_serato_crate_bytes_rejects_unsafe_relative_paths(bad_path: str) -> None:
    with pytest.raises(ValueError, match="relative crate path"):
        build_serato_crate_bytes([bad_path])


def test_parse_serato_crate_bytes_returns_version_and_ordered_paths() -> None:
    crate_bytes = build_serato_crate_bytes(["Music/A.flac", "Music/B.flac"])

    parsed = parse_serato_crate_bytes(crate_bytes)

    assert parsed.version == SERATO_CRATE_VERSION
    assert parsed.paths == ("Music/A.flac", "Music/B.flac")


def test_parse_serato_crate_bytes_handles_repeated_otrk_records_and_reports_unknown_tags() -> None:
    crate_bytes = b"".join(
        [
            tlv(b"vrsn", utf16be(SERATO_CRATE_VERSION)),
            tlv(b"zzzz", b"top-level diagnostic"),
            tlv(b"otrk", tlv(b"aaaa", b"nested diagnostic") + tlv(b"ptrk", utf16be("Music/A.flac"))),
            tlv(b"otrk", tlv(b"ptrk", utf16be("Music/B.flac"))),
        ]
    )

    parsed = parse_serato_crate_bytes(crate_bytes)

    assert parsed.paths == ("Music/A.flac", "Music/B.flac")
    assert parsed.unknown_tags == ("zzzz", "otrk.aaaa")


def test_parse_serato_crate_bytes_rejects_truncated_tlv_records() -> None:
    with pytest.raises(SeratoCrateParseError, match="truncated TLV payload"):
        parse_serato_crate_bytes(b"vrsn" + (10).to_bytes(4, "big") + b"short")


def test_validate_serato_crate_bytes_accepts_generated_bytes_for_expected_ordered_paths() -> None:
    crate_bytes = build_serato_crate_bytes(["Music/A.flac", "Music/B.flac"])

    report = validate_serato_crate_bytes(crate_bytes, ["Music/A.flac", "Music/B.flac"])

    assert report.valid is True
    assert report.version == SERATO_CRATE_VERSION
    assert report.paths == ("Music/A.flac", "Music/B.flac")
    assert report.expected_paths == ("Music/A.flac", "Music/B.flac")
    assert report.errors == ()


def test_validate_serato_crate_bytes_reports_path_order_mismatch() -> None:
    crate_bytes = build_serato_crate_bytes(["Music/A.flac", "Music/B.flac"])

    report = validate_serato_crate_bytes(crate_bytes, ["Music/B.flac", "Music/A.flac"])

    assert report.valid is False
    assert report.errors == ("path order mismatch",)


def test_validate_serato_crate_bytes_reports_version_mismatch() -> None:
    crate_bytes = tlv(b"vrsn", utf16be("0.9/Unexpected")) + tlv(b"otrk", tlv(b"ptrk", utf16be("Music/A.flac")))

    report = validate_serato_crate_bytes(crate_bytes, ["Music/A.flac"])

    assert report.valid is False
    assert report.version == "0.9/Unexpected"
    assert report.errors == ("version mismatch: expected 1.0/Serato ScratchLive Crate, got 0.9/Unexpected",)


def test_validate_serato_crate_bytes_reports_malformed_bytes() -> None:
    crate_bytes = b"otrk" + (12).to_bytes(4, "big") + b"short"

    report = validate_serato_crate_bytes(crate_bytes, ["Music/A.flac"])

    assert report.valid is False
    assert report.version is None
    assert report.paths == ()
    assert report.errors == ("malformed crate: truncated TLV payload for tag 'otrk': length 12 exceeds remaining 5",)


def test_plan_serato_crate_export_returns_dry_run_preview_without_writing(tmp_path) -> None:
    plan = plan_serato_crate_export("Warmup", ["Music/A.flac"], tmp_path)

    assert isinstance(plan, SeratoExportPlan)
    assert plan.target_path == tmp_path / "_Serato_" / "Subcrates" / "Warmup.crate"
    assert plan.backup_path == tmp_path / "_Serato_" / "Subcrates" / "Warmup.crate.bak"
    assert plan.track_count == 1
    assert plan.preview()["will_write"] is False
    assert not plan.target_path.exists()


def test_write_serato_crate_requires_confirm_and_does_not_write_by_default(tmp_path) -> None:
    plan = plan_serato_crate_export("Warmup", ["Music/A.flac"], tmp_path)

    with pytest.raises(PermissionError, match="confirm=True"):
        write_serato_crate(plan)

    assert not plan.target_path.exists()


def test_write_serato_crate_confirmed_creates_backup_then_writes_bytes_and_validates(tmp_path) -> None:
    plan = plan_serato_crate_export("Warmup", ["Music/A.flac"], tmp_path)
    plan.target_path.parent.mkdir(parents=True)
    plan.target_path.write_bytes(b"existing")

    result = write_serato_crate(plan, confirm=True)

    assert result.written_path == plan.target_path
    assert result.backup_path == plan.backup_path
    assert result.validated is True
    assert result.rollback_available is True
    assert result.rollback_action == "restore_backup"
    assert plan.backup_path.read_bytes() == b"existing"
    assert plan.target_path.read_bytes() == build_serato_crate_bytes(["Music/A.flac"])
    assert validate_serato_crate_file(plan) is True


def test_rollback_serato_crate_write_restores_backup(tmp_path) -> None:
    plan = plan_serato_crate_export("Warmup", ["Music/A.flac"], tmp_path)
    plan.target_path.parent.mkdir(parents=True)
    plan.target_path.write_bytes(b"existing")
    result = write_serato_crate(plan, confirm=True)

    rollback_serato_crate_write(result)

    assert plan.target_path.read_bytes() == b"existing"


def test_rollback_serato_crate_write_deletes_new_crate_when_no_backup_exists(tmp_path) -> None:
    plan = plan_serato_crate_export("Warmup", ["Music/A.flac"], tmp_path)
    result = write_serato_crate(plan, confirm=True)

    assert result.backup_path is None
    assert result.rollback_available is True
    assert result.rollback_action == "delete_created_crate"

    rollback_serato_crate_write(result)

    assert not plan.target_path.exists()
