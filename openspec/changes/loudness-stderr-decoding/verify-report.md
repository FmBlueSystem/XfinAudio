# Verification
- RED: 6 failed / 2 passed, with actual UnicodeDecodeError and cached transient failure.
- GREEN: 208 focused adapter, lifecycle, completion, numerical, runtime and repository tests passed.
- Full-project Pyright: zero errors; Ruff lint and format checks passed.
- Independent read-only review found no parser-safety blocker to replacement decoding;
  corrupted numeric/unit tokens still reject, unlike deletion with errors=ignore.
- No user audio, tag writes, credentials, provider calls or Qt accessibility changes.
- Existing cached failure needs selected-track Reanalyze loudness / force_reanalyze.
- Native one-copy retest, final aggregate gate and publication remain coordinator-owned.
