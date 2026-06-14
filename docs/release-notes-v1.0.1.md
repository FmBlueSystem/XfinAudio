# XfinAudio 1.0.1 Release Notes

Date: 2026-06-14

## Summary

XfinAudio 1.0.1 is a polish and hardening release following the initial open-source release. It adds keyboard accessibility, documents the update path, and automates PyPI publication so future releases can be published by pushing a `v*` tag.

## Who should use it

- DJs and testers running macOS with a Mixed In Key processed audio library.
- Users comfortable installing a Python package via `pip`, `pipx`, or `uv tool`.

## What is included

- Global keyboard shortcuts for the main desktop workflow (Ctrl+O, Ctrl+S, Ctrl+R, Ctrl+E, Esc).
- Accessible names and logical tab order across Library, Build, Review, Export, and Metadata screens.
- Documented update path preserving `~/.xfinaudio/` database and settings across package updates.
- Tag-triggered GitHub Actions workflow that publishes to PyPI automatically.
- Automated release gate evidence generation (JSON + Markdown).

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

- Automated tests: `uv run pytest -q` — 741 passed.
- Coverage: `uv run pytest --cov --cov-fail-under=70 -q` — 89.17%.
- Ruff lint: `uv run ruff check .` — pass.
- Ruff format check: `uv run ruff format --check .` — pass.
- Type check: `uv run pyright src tests` — 0 errors.
- Release smoke: `uv run python scripts/smoke_release_readiness.py` — pass.
- Release gates: `uv run python scripts/release_gate_check.py --run` — pass.
- PyPI publication: https://pypi.org/project/xfinaudio/1.0.1/
- Manual desktop QA: pending (requires real Mixed In Key processed audio folder).

## Known limitations

- Serato fixture validation is not live Serato compatibility.
- Live Serato library writes are not verified as part of this release candidate; any Serato crate export must be treated as experimental and requires a manual backup and verification step.
- Manual desktop QA with a real Mixed In Key processed folder is required before release claims.
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

## Support and troubleshooting

- Re-run the release smoke script before reporting release-readiness failures.
- Include platform, command output, and relevant evidence links in reports.
- Issue tracker: https://github.com/FmBlueSystem/XfinAudio/issues
