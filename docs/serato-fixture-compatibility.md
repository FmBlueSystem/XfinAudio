# Serato Fixture Compatibility

Date: 2026-06-03

## Scope

XfinAudio validates Serato crate compatibility with deterministic fixture bytes only. The validator is read-only and accepts bytes supplied by tests or planned export artifacts; it does not discover, read, or mutate a live Serato library.

## Supported crate subset

The supported fixture subset is the deterministic TLV structure emitted by `build_serato_crate_bytes`:

- TLV header: 4-byte ASCII tag followed by a 4-byte big-endian payload length.
- `vrsn`: top-level UTF-16BE string. Expected value: `1.0/Serato ScratchLive Crate`.
- `otrk`: top-level track record containing nested TLV records.
- `ptrk`: nested `otrk` UTF-16BE track path string.
- Repeated `otrk` records preserve path order.
- Unknown top-level tags are ignored for compatibility decisions and listed in diagnostics.
- Unknown nested `otrk` tags are ignored for compatibility decisions and listed as `otrk.<tag>` diagnostics.

Malformed TLV records fail validation when a header is truncated, a payload length exceeds the remaining bytes, a tag is not ASCII, or supported text payloads are not valid UTF-16BE.

## Validation report

`validate_serato_crate_bytes(crate_bytes, expected_paths)` returns a read-only report with:

- `valid`: whether version and ordered paths match.
- `version`: parsed crate version, or `None` when bytes are malformed.
- `paths`: parsed ordered `ptrk` paths.
- `expected_paths`: caller-provided expected ordered paths.
- `errors`: path/version/malformed validation reasons.
- `unknown_tags`: ignored top-level or nested unknown tags for diagnostics.

## What this proves

This proves that XfinAudio-generated fixture bytes match the documented TLV assumptions for version and ordered track paths, and that malformed bytes produce a safe validation failure.

## What this does not prove

This does not prove live Serato import compatibility. It does not parse or mutate Serato database V2 files, it does not write to a live Serato library, and it does not read or write audio files.

## Safety posture

Write safety is unchanged. Planning remains dry-run by default. Confirmed crate writes still require `confirm=True`, create a backup when replacing an existing crate, validate the written bytes against the planned artifact, and expose rollback guidance.
