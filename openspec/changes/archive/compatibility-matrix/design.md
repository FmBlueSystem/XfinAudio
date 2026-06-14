# Design: Compatibility Matrix

## Overview

Document the Serato compatibility boundary as a matrix. The project validates crate bytes against deterministic fixtures, not live Serato libraries. The matrix makes this explicit per Serato version range.

## Matrix rows

| Serato version range | Fixture validation | Live import | Notes |
|----------------------|--------------------|-------------|-------|
| Serato DJ Pro 2.x+ (assumed) | Verified by fixture bytes | Not verified | Crate format assumed stable for the documented TLV subset. |
| Older Serato ScratchLive crates | Not verified | Not verified | Legacy crate formats are out of scope. |

## Cross-references

- `docs/serato-fixture-compatibility.md` explains the validation subset.
- `docs/release-notes-template.md` warns that fixture validation is not live compatibility.

## Test

`tests/test_serato_compatibility_matrix.py` asserts the matrix document:
- Exists.
- Contains a Markdown table.
- Mentions "live" and "fixture".

## Safety

- Documentation-only change; no code behavior changes.
