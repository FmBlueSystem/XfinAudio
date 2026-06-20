# Proposal: Smoke shutdown stability

## Intent

Make XfinAudio package-smoke startup/shutdown stable by preventing background spectral completion work from starting or emitting signals while `XFINAUDIO_PACKAGE_SMOKE=1` exits immediately after initialization.

## Problem

The local smoke command exits with code 0, but logs a spectral completion worker traceback during interpreter shutdown. That makes launch validation noisy and can hide real startup failures.

## Scope

In scope:

- Prevent spectral completion worker startup during package smoke mode.
- Add focused test coverage for smoke mode behavior.
- Preserve normal desktop runtime behavior outside smoke mode.

Out of scope:

- New DSP or audio analysis behavior.
- Audio file mutation.
- Live Serato DB V2 writes.
- Export format or writer changes.
- UI redesign.

## Success Criteria

- Smoke mode exits without spectral completion worker traceback.
- Focused test proves smoke mode does not start spectral completion work.
- Normal non-smoke path remains unchanged.
- Full verification gates pass.
