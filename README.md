# XfinAudio

XfinAudio is a GPL-3.0-only desktop DJ playlist assistant for building metadata-driven playlist recommendations. It is an early, local desktop project intended for source publication and contributor review; it is not a cleared binary distribution.

## Status

- License posture: full open source under GPL-3.0-only. See `LICENSE` and `docs/open-source-license.md`.
- Packaging posture: source/dev use is documented; binary/app bundle redistribution remains pending legal review.
- Release posture: signing, notarization, DMG creation, and release publishing are not claimed complete.
- Publication checklist: follow `docs/repository-publication-checklist.md` before turning a local tree into a public source repository.

## Quick start for development

Requirements: Python 3.11 and `uv`.

```bash
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Launch the local desktop app for manual QA:

```bash
uv run xfinaudio
```

## What it does

XfinAudio scans existing track metadata, scores transitions, explains recommendations, and exports playlist artifacts. It is designed around DJs who already manage audio and metadata outside the app.

For harmonic scoring concepts, Camelot movement, strategy intent, and current non-goals, see [HARMONIC_MIXING.md](HARMONIC_MIXING.md).

## Safety posture and non-goals

XfinAudio is intentionally non-destructive:

- It does not mutate audio files.
- It does not render, mix, time-stretch, pitch-shift, or analyze waveforms.
- It does not perform key detection, BPM detection, beat tracking, or cue/phrase detection.
- It does not mutate live Serato database V2 files.
- The app writes only its app-owned database, settings, and export files.
- Serato crate writes are only through the explicit safe export/backup/validation flow documented in the project.

## Release gates

Before any release claim, run the automated gates and record the manual gates described in `docs/release-readiness-smoke.md`:

```bash
uv run python scripts/release_gate_check.py --run
uv run python scripts/smoke_release_readiness.py
```

Manual desktop QA is still required for real user workflows. Clean macOS account validation, signing, notarization, DMG checks, and binary redistribution review remain separate pending gates.

## License and dependency caveats

Source code is distributed under GPL-3.0-only. Redistribution must comply with GPLv3 and third-party dependency obligations.

No legal advice or legal clearance is implied by this repository documentation. Binary/app bundle redistribution needs legal review for PySide6/Qt, mutagen, and other third-party dependencies. See `NOTICE.md`, `docs/open-source-license.md`, and `docs/third-party-license-inventory.md`.
