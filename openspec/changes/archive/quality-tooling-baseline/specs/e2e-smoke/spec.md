# Spec: Real-Audio E2E Smoke Test

## Goal

Automate the manual `real Mixed In Key audio QA` gate with a single deterministic end-to-end smoke test that exercises scan → persist → recommend → Serato export against a real audio fixture.

## Acceptance Criteria

- A new test file `tests/test_smoke_real_audio_scan_recommend_export.py` is created.
- The test copies the committed `tests/fixtures/silence_1s.wav` into a temporary directory.
- The test writes Mixed In Key-style metadata (BPM, Camelot key, energy, title, artist, genre) into the copy using mutagen.
- The test scans the temporary folder using the real `MetadataScanService`.
- The test persists the scanned records using `TrackRepository`.
- The test recommends a playlist using `PlaylistWorkflowService`.
- The test plans and writes a Serato crate into a temporary `_Serato_/Subcrates` folder.
- The test asserts that the crate contains the expected track path.
- `openspec/config.yaml` records `e2e.available: true`.

## Constraints

- The test must not write to the user's real Serato library.
- The test must not mutate the committed fixture.
- The test must not require external services or real Mixed In Key installation.

## Behavior Changes

None. This is a test-only addition.
