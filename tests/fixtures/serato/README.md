# SYNTHETIC Serato fixtures — not real DJ data

Everything under `_Serato_/` is hand-built by `serato_fixture_builder.py`
(run it directly to regenerate deterministically). It follows the spike's
database V2 TLV framing hypothesis:

- record framing: 4-byte ASCII tag + big-endian u32 payload length,
- typed values: 1-byte type code (`t` UTF-16BE string, `o` associative
  array, `j` unix-milliseconds timestamp, `u` uint8).

## WARNING: tags are unverified

The field tags used here (`osen`, `pfil`, `ttit`, `tart`, `ptim`) are
plausible placeholders for the spike only. They MUST be verified against a
sanitized live Serato sample before any production trust. The reader's
unknown-field tolerance is what makes this safe to probe with.
