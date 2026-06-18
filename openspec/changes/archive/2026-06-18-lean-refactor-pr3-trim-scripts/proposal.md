## Why

`scripts/` carries four dead artifacts that have no callers in the repo and are not
documented in README, CONTRIBUTING, or `docs/`. They invite confusion about what is
supported and inflate the release-gate check surface.

## What changes

- **Delete** `scripts/benchmark_spectral_analysis.py` (360 LOC) — one-shot spectral
  measurement script, no caller, no docs reference, no CI invocation.
- **Delete** `scripts/validate_spectral_colors.py` (96 LOC) — one-shot spectral color
  validator, no caller, no docs reference, no CI invocation.
- **Delete** `scripts/alert_user.sh` (16 LOC) — bash script generating a beep with
  `sox` + `afplay`. No caller, no docs reference.
- **Delete** `scripts/xfinaudio-launcher.sh` (18 LOC) — bash macOS launcher wrapping
  the venv Python. No caller, no docs reference, undocumented in README/CONTRIBUTING.

## What stays

- `scripts/fill_spanish_translations.py` — referenced by `pyproject.toml` (lint ignore
  list) and `README.md` (translation workflow).
- `scripts/update_translations.py` — referenced by `README.md`, `scripts/fill_spanish_translations.py`,
  and `src/xfinaudio/desktop/i18n.py`.
- `scripts/release_gate_check.py`, `scripts/source_package_hygiene_check.py`,
  `scripts/performance_baseline.py`, `scripts/manual_mik_qa_harness.py`,
  `scripts/inspect_mik_tags.py`, `scripts/screenshot_app_before_scan.py`,
  `scripts/screenshot_app_with_colors.py`, `scripts/smoke_release_readiness.py`,
  `scripts/render_release_gate_evidence.py`, `scripts/pyinstaller_build_smoke.py`,
  `scripts/package_install_smoke.py`, `scripts/third_party_license_inventory.py` —
  all referenced by `release_gate_check.py` or the GitHub workflows.

No source code changes. No public API impact. No test changes.

## Non-goals

- Refactoring `main_window.py` (PR 5).
- Collapsing controller/coordinator/presenter/worker files in `desktop/` (PR 4).
- Re-implementing the launcher in Python (no consumer; recoverable from git history).
- Touching the translation scripts.

## Impact

- Net: ~490 LOC removed across 4 files.
- Review budget: trivially under 400-line cap.
- Risk: low — every deletion is verified to have zero callers in `src/`, `tests/`,
  `packaging/`, `docs/`, `.github/`, or any tracked file.
