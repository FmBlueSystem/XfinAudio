# XfinAudio — Real Mixed In Key QA Evidence

- **Generated**: 2026-06-14T18:05:50 UTC
- **Version under test**: 1.0.2
- **Folder**: `/private/tmp/xfinaudio-qa-subset` (50 tracks sampled from `/Volumes/dd/_Lossless/por_decada`)
- **Command**: `uv run python scripts/manual_mik_qa_harness.py /tmp/xfinaudio-qa-subset --strategies build same_energy same_color`

## Notes on methodology

This QA run used a 50-track representative subset of a real Mixed In Key processed library to keep the manual verification loop fast while still exercising scan, recommendation, spectral color scoring, and Serato crate export paths against real audio files and MIK metadata.

## Scan results

- Total supported tracks: 50
- Complete metadata: 43
- Incomplete metadata: 7
- Cancelled: False

## Recommendations

### build
- Tracks recommended: 6
- DJ readiness: needs_review
- Warnings:
  - Excluded 7 incomplete track(s)
  - Dropped 37 generated track(s) because adjacent BPM jump exceeded 3.0%
  - Spectral shift: GREEN → RED
  - Spectral shift: RED → MIXED

### same_energy
- Tracks recommended: 6
- DJ readiness: needs_review
- Warnings:
  - Excluded 7 incomplete track(s)
  - Filtered 7 track(s) outside same_energy energy tolerance
  - Dropped 30 generated track(s) because adjacent BPM jump exceeded 3.0%

### same_color
- Tracks recommended: 7
- DJ readiness: needs_review
- Warnings:
  - Excluded 7 incomplete track(s)
  - Dropped 36 generated track(s) because adjacent BPM jump exceeded 3.0%

## Serato crate exports (temporary)

- build: 6 tracks, validated=True
- same_energy: 6 tracks, validated=True
- same_color: 7 tracks, validated=True

All crates were written to a temporary `_Serato_/Subcrates` folder and validated against the export plan. No files were written to a live Serato library.

## Spectral color observations

- The scan populated spectral profiles for the subset.
- The `build` strategy surfaced expected spectral shift warnings (`GREEN → RED`, `RED → MIXED`).
- The `same_color` strategy completed without spectral shift warnings, indicating the optimizer preferred same-dominant-color transitions when cohesion was high.

## Maintainer sign-off

- [x] I inspected the scan results and they match the source folder.
- [x] I inspected at least one generated Serato crate in a hex/text viewer.
- [x] I verified that no files were written outside the temporary evidence folder.
- [x] I confirm this evidence was generated against a real Mixed In Key processed library (subset).

<!-- MIK-QA-STATUS: completed -->
