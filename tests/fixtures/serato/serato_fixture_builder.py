"""SYNTHETIC Serato fixture builder for the read-only history spike.

Everything produced here is hand-built test data shaped like the Serato
database V2 TLV hypothesis the spike validates. It contains no real DJ data
and its field tags are NOT verified against a sanitized live Serato sample;
see README.md in this directory before trusting the tags in production.

The typed-value encoder mirrors (and pins) the framing the production reader
in ``xfinaudio.exporting.serato_history`` must tolerate:

- record framing: 4-byte ASCII tag + big-endian u32 payload length,
- typed values: 1-byte type code prefix, then the type-specific value.

Running this module directly regenerates the static binary fixtures under
``tests/fixtures/serato/_Serato_`` deterministically.
"""

from __future__ import annotations

from pathlib import Path

from xfinaudio.exporting.serato_crate import build_serato_crate_bytes

FIXTURES_DIR = Path(__file__).resolve().parent
SERATO_TREE_DIR = FIXTURES_DIR / "_Serato_"

TRACK_ONE_PATH = "Music/track_one.flac"
TRACK_TWO_PATH = "Music/track_two.flac"
TRACK_THREE_PATH = "Music/track_three.flac"

TRACK_ONE_PLAYED_AT_MS = 1704067200000  # 2024-01-01T00:00:00Z
TRACK_TWO_PLAYED_AT_MS = 1704153600000  # 2024-01-02T00:00:00Z


def tlv(tag: bytes, payload: bytes) -> bytes:
    """Frame one record: 4-byte ASCII tag + big-endian u32 length + payload."""
    if len(tag) != 4:
        raise ValueError("TLV tag must be exactly 4 bytes")
    return tag + len(payload).to_bytes(4, "big") + payload


def encode_typed_string(value: str) -> bytes:
    """Encode a UTF-16BE string value with the spike's 't' type prefix."""
    return b"t" + value.encode("utf-16-be")


def encode_typed_timestamp(unix_ms: int) -> bytes:
    """Encode a unix-milliseconds timestamp with the spike's 'j' type prefix."""
    return b"j" + unix_ms.to_bytes(8, "big")


def encode_typed_uint8(value: int) -> bytes:
    """Encode a uint8 value with the spike's 'u' type prefix."""
    return b"u" + value.to_bytes(1, "big")


def encode_assoc(*records: bytes) -> bytes:
    """Encode an 'o' associative-array payload from pre-framed records."""
    return b"o" + b"".join(records)


def build_session_bytes(
    *,
    track_path: str,
    title: str,
    artist: str | None,
    played_at_ms: int,
) -> bytes:
    """Build one minimal synthetic history session file."""
    track_records = [
        tlv(b"pfil", encode_typed_string(track_path)),
        tlv(b"ttit", encode_typed_string(title)),
    ]
    if artist is not None:
        track_records.append(tlv(b"tart", encode_typed_string(artist)))
    track_records.append(tlv(b"ptim", encode_typed_timestamp(played_at_ms)))

    version_record = tlv(b"vrsn", encode_typed_string("1.0/Serato DJ History"))
    session_record = tlv(b"osen", encode_assoc(*track_records))
    return version_record + session_record


def build_unknown_type_session_bytes() -> bytes:
    """Build a session holding an unknown root tag and an unknown track sub-tag."""
    track_records = [
        tlv(b"pfil", encode_typed_string(TRACK_ONE_PATH)),
        tlv(b"ttit", encode_typed_string("Track One")),
        tlv(b"tart", encode_typed_string("Artist One")),
        tlv(b"ptim", encode_typed_timestamp(TRACK_ONE_PLAYED_AT_MS)),
        tlv(b"qnew", encode_typed_uint8(7)),  # unknown sub-tag, known type
    ]
    version_record = tlv(b"vrsn", encode_typed_string("1.0/Serato DJ History"))
    session_record = tlv(b"osen", encode_assoc(*track_records))
    unknown_root_record = tlv(b"xtrk", b"Z" + b"\x00\x01\x02\x03")  # unknown type 'Z'
    return version_record + session_record + unknown_root_record


def build_serato_fixture_tree(root: Path = SERATO_TREE_DIR) -> None:
    """Regenerate the static SYNTHETIC _Serato_ fixture tree deterministically."""
    sessions_dir = root / "History" / "sessions"
    subcrates_dir = root / "Subcrates"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    subcrates_dir.mkdir(parents=True, exist_ok=True)

    (sessions_dir / "session_2024_01_01").write_bytes(
        build_session_bytes(
            track_path=TRACK_ONE_PATH,
            title="Track One",
            artist="Artist One",
            played_at_ms=TRACK_ONE_PLAYED_AT_MS,
        )
    )
    (sessions_dir / "session_2024_01_02").write_bytes(
        build_session_bytes(
            track_path=TRACK_TWO_PATH,
            title="Track Two",
            artist=None,
            played_at_ms=TRACK_TWO_PLAYED_AT_MS,
        )
    )
    (subcrates_dir / "House.crate").write_bytes(build_serato_crate_bytes([TRACK_ONE_PATH, TRACK_THREE_PATH]))
    (subcrates_dir / "PeakTime.crate").write_bytes(build_serato_crate_bytes([TRACK_ONE_PATH, TRACK_TWO_PATH]))


if __name__ == "__main__":
    build_serato_fixture_tree()
    print(f"regenerated SYNTHETIC fixtures under {SERATO_TREE_DIR}")
