# v2.0.0 release-gate remediation — 2026-09-28

## What happened

Tag `v2.0.0` (= `main@5ca3433`, pushed to GitHub, DMG built) shipped without a
release-gate run. Running `scripts/release_gate_check.py --run` on the tagged
candidate failed:

- FAIL `type-check`: 11 pyright errors in 6 test files.
- (latent) FAIL `format`: 10 test files deviating from `ruff format`, pre-existing
  on the base commit — surfaced when `5ca3433`'s `uv.lock` bump moved ruff.
- PASS everything else (tests+coverage, lint, smokes, hygiene, PyInstaller).

The v2 ledger (`odd/tasks/version-2-scientific-foundation.md`) recorded
"ruff/pyright clean" per slice on the working branch, but the final tagged
candidate was never gate-checked. Root cause is process, not code.

## Remediation (branch `fix/v2-release-gate`)

| Commit | Content |
| --- | --- |
| `46fa8dd` | fix(tests): typing-only fixes for the 11 pyright errors |
| `f1e0d31` | style(tests): ruff format on the 10 deviating files (format-only) |

## Gate result after remediation

Full `release_gate_check.py --run` on this branch: **all automated gates PASS**
(tests+coverage, type-check, lint, format, release readiness smoke,
open-source publication docs, publication artifact hygiene, source package
hygiene, PyInstaller check-only, root artifact hygiene). Manual gate
`mik-manual-audio-qa`: COMPLETED (`docs/qa-manual-mik-evidence.md` carries the
completed marker).

Machine-readable evidence: `release-gate-evidence.json` in this directory.

## Open decision

The pushed `v2.0.0` tag still points at the non-gate-green commit. Recommended:
fix-forward as `v2.0.1` (bump + this branch + gate evidence). Moving a pushed
tag is bad practice.
