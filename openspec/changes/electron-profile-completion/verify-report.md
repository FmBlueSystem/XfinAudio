# Verification: Python completion/scoring slice

2026-10-01. Local V9 checkout only; nothing pushed, merged or released. Host/renderer evidence lives in frontend.md. Final combined release-gate evidence is recorded separately.

## RED → GREEN evidence

- Initial completion contract: 10 failed, then 10 passed
- Preference/original scoring propagation: 11 failed, then 21 combined passed
- Race regressions: 2 failed (source swap inside persistence, late acknowledged cancellation), then 24 unit/lifecycle cases passed
- Backend composition: unknown-method RED before Library/Saved adapter wiring; GREEN after wiring

## Final checks

- Qt-free v9/.venv, PYTHONPATH=src, pytest --noconftest -q tests/test_headless_*.py: 519 passed, 1 explicitly Qt-only compatibility skip (26.16s). This run preceded addition of the actual-silence fixture test below; all production completion/scoring code and integrated review/offline adapters were included.
- Same interpreter, tests/test_headless_profiles.py + tests/test_track_repository.py: 144 passed, zero skips (10.54s), including the final added actual-silence test
- Review controls + Serato export + Live: 91 passed, 1 explicitly Qt-only skip
- Focused Pyright: 0 errors, 0 warnings; Ruff lint and format check pass for completion/preferences/scoring/lifecycle/repository/new tests
- New runtime installation succeeded with uv pip sync --require-hashes against desktop-electron/requirements-headless.txt; find_spec('PySide6') returned None. Original librosa 0.11.0 modules import and execute normally in this interpreter.

## Requirement evidence

- Reuse and order: original LibrosaSpectralAnalyzer, LibrosaDanceabilityAnalyzer, LibrosaEdgeSpectralAnalyzer; exact spectral → danceability → edge ordering and bounded job ownership tested
- Genuine engine behavior: three disposable 70-second audible FLACs generated locally, all three original profiles persisted; Same Color and Same Color & Energy each returned three eligible tracks; byte SHA-256 and mtime_ns unchanged
- Honest unavailable: original engines on a separate 70-second silent FLAC produced zero successful profiles, partial state and one failed/pending track, with unchanged source SHA/mtime. Mocked dependency absence produces unavailable rather than fabricated values; decoder and persistence failures produce partial counts without exposing private paths.
- Current cache: restart and repeat completion reuse profiles; obsolete analysis versions and changed/symlink/missing sources are rejected. Both status and original scoring receive only current profiles. Original repository updates retain backward compatibility when optional expected_file_identity is omitted.
- Cancellation: pre/during/late cancellation, exclusive busy rejection, shutdown drain, no late publication/persistence, and retry after cancellation covered
- Preferences: original 0.5 default, exact finite [0,1] validation, revision conflict and restart, immutable preservation of volume/watch and other settings; current policy reaches all original Prep variants and Live ranking. Saving cohesion invalidates scoring-dependent reviews/Live/AI but preserves unrelated editor draft session.
- Safety: no analyzer code changed, no new DSP, no provider request, no loudness/tag write, no Serato database V2 write. Synthetic fixtures only; installed settings and user audio untouched.

## Remaining verification boundaries

This focused report does not claim the aggregate legacy release gate, native Mac completion, full-library stress or signed packaging. Final validation includes the combined aggregate gate and separate frozen-runtime checks for every declared audio format and bundled-FFmpeg fallback. The existing Qt application remains rollback.
