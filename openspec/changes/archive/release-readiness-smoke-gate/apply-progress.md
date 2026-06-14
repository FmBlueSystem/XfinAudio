# Apply Progress: Release Readiness Smoke Gate

## Summary

All planned tasks were applied. The existing `scripts/smoke_release_readiness.py` was hardened with a DJ readiness report and promoted to a first-class automated release gate. The runbook at `docs/release-readiness-smoke.md` was preserved and updated to reference the new gate and the DJ readiness pass line.

## Key decisions

- Added a DJ readiness step using `build_dj_readiness_report` without passing a Serato plan, so the smoke stays dry-run and does not require real track files on disk.
- Registered the smoke as a `release_gate_check.py` command gate placed between format and open-source publication docs.
- Restored the original comprehensive runbook content and updated it with the new gate and checklist line.

## Files changed

- `scripts/smoke_release_readiness.py`
- `scripts/release_gate_check.py`
- `tests/test_release_gate_check.py`
- `tests/test_release_smoke.py`
- `docs/release-readiness-smoke.md`
