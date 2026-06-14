# XfinAudio 1.0.2 Release Notes

Date: 2026-06-14

## Summary

XfinAudio 1.0.2 adds spectral color intelligence to the recommendation workflow. Metadata scans now return tracks immediately while spectral colors are completed in the background, and DJs can control how much spectral color influences playlist cohesion via a new "Spectral Cohesion" slider plus a dedicated "Same Color" strategy.

## Who should use it

- DJs and testers running macOS with a Mixed In Key processed audio library.
- Users who want visible spectral color badges and cohesion-aware recommendations.

## What is included

- **Lazy spectral completion worker**: the library table appears immediately after a metadata scan; spectral colors are computed progressively in a background thread and persisted to the app database.
- **Spectral Cohesion slider** in Build Playlist (0%–100%): controls how strongly adjacent tracks should share a similar spectral color profile.
- **Same Color strategy**: a preset that emphasizes spectral similarity for a cohesive timbre while retaining harmonic, BPM, energy, and tag components.
- **Color-dominant penalty** in transition scoring: when cohesion is high, transitions between different dominant colors (RED/GREEN/BLUE/MIXED) receive a small score penalty.
- **Backward-compatible scoring**: the new effects are disabled when cohesion is 0%; app default is 50%.
- **Persistent setting**: the slider value is saved in `~/.xfinaudio/settings.json` and restored on launch.

## License posture

- XfinAudio source is full open source under GPL-3.0-only.
- Redistribution must comply with GPLv3 and third-party dependency obligations.
- PySide6/Qt, mutagen, and dependency obligations remain pending legal review before binary/app bundle redistribution.
- No legal clearance is implied by these notes.

## Explicitly out of scope

- No audio file mutation.
- No live Serato writes.
- No installer, signing, notarization, or DMG distribution.
- No claim of live Serato compatibility beyond fixture-based validation.

## Verification evidence

- Automated tests: `uv run pytest -q` — 778 passed.
- Coverage: `uv run pytest --cov --cov-fail-under=70 -q` — 88.15%.
- Ruff lint: `uv run ruff check .` — pass.
- Ruff format check: `uv run ruff format --check .` — pass.
- Type check: `uv run pyright src tests` — 0 errors.
- Release smoke: `uv run python scripts/smoke_release_readiness.py` — pass.
- Release gates: `uv run python scripts/release_gate_check.py --run` — pass.
- Manual desktop QA: completed 2026-06-14 against `/Volumes/dd/_Lossless/por_decada` — evidence: `docs/qa-manual-mik-evidence.md`.

## Known limitations

- Spectral analysis relies on read-only audio loading and may fall back to `audioread` for some formats, emitting a benign deprecation warning.
- Serato fixture validation is not live Serato compatibility.
- Live Serato library writes are not verified as part of this release candidate; any Serato crate export must be treated as experimental and requires a manual backup and verification step.
- Binary redistribution legal review remains pending for PySide6/Qt, mutagen, and third-party dependencies.

## Safe-use warnings

- XfinAudio must not mutate source audio files.
- Do not write to a live Serato library from this release candidate.
- Use safe export folders outside the scanned audio library.
- Treat fixture-based Serato checks as dry-run validation only.

## Upgrade and data notes

- App database path: `~/.xfinaudio/xfinaudio.sqlite3`.
- Settings path: `~/.xfinaudio/settings.json`.
- Installing or upgrading via `pip install --upgrade xfinaudio`, `pipx upgrade xfinaudio`, or `uv tool upgrade xfinaudio` preserves these files.
- The database schema has been extended to store spectral profiles; older databases are migrated automatically on first use.

## Support and troubleshooting

- Re-run the release smoke script before reporting release-readiness failures.
- Include platform, command output, and relevant evidence links in reports.
- Issue tracker: https://github.com/FmBlueSystem/XfinAudio/issues
