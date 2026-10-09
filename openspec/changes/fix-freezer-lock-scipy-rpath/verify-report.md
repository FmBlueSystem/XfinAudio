# Verify report — fix-freezer-lock-scipy-rpath

Date: 2026-10-08. All evidence below is from this worktree
(`/tmp/xfin-fix-232`, branch `fix/freezer-lock-scipy-1.18.1`, base `ac4abd5`)
unless stated otherwise.

## RED (reproduced failure on `ac4abd5`)

- `packaging/macos/build.py` on the v2.3.1 build tree failed at
  `packaging/macos/dependencies.py` L131: `Runtime rpath escapes bundle`,
  offender `core-dist/xfinaudio-core/_internal/libgfortran.5.dylib` — the
  flattened copy of scipy 1.17.1's wheel dylib whose install id
  (`/DLC/scipy/.dylibs/libgfortran.5.dylib`) escapes the bundle after
  PyInstaller 6.20.0's destination-relative `@rpath` rewrite.
- The pre-downgrade lock set (2.2.0 build, same PyInstaller) froze audit-clean,
  isolating the lock contents as the cause.

## GREEN (fix branch)

- Lock regeneration: semantic pin diff across
  `desktop-electron/requirements-headless.txt` and
  `packaging/linux/requirements-build.txt` is exactly
  llvmlite 0.47.0 → 0.50.0, numba 0.65.1 → 0.68.0, numpy 2.4.6 → 2.5.3,
  scipy 1.17.1 → 1.18.1; `packaging/macos/requirements-build.txt` unchanged
  (`macholib==1.16.4` + Linux lock).
- Lock consistency: `tests/test_headless_requirements_lock_drift.py` 8/8 green.
- Documentation consistency tests: 23/23 green after the version/docs sync.
- Full gate (`release_gate_check.py --run`, JSON evidence `/tmp/gate-232.json`):
  9/9 automated gates passed — tests and coverage (2,823 tests, coverage
  91.81%, floor 89.0%), type-check (pyright 0 errors), lint, format, release
  readiness smoke, open-source publication docs, publication artifact hygiene,
  source package hygiene, root artifact hygiene.
- Electron suite (fresh run on this tree, `.venv-headless` from the restored
  lock, Electron dist 43.3.0 arm64): 528/528 passed, 0 failed, 0 skipped,
  0 cancelled in 58.9 s.
- Gated macOS build probe (`build.py` with the sealed gate report): passed gate
  validation, dependency-manifest validation, environment validation (macholib 1.16.4 +
  restored lock pins in the freezer venv), freeze, and the post-freeze native audit
  (`audit_tree` on the frozen core) — the exact check that failed on `ac4abd5`. The probe
  then reached `assemble` for the first time this cycle and exposed the latent Electron
  version contract (below); the full bundle assembly was re-run after the pin fix, with the
  final outcome recorded in the PR evidence and the DMG ceremony.
- Discovery: `assemble` requires exact equality between the fetched Electron `dist/version`
  and `devDependencies.electron`; the caret range `^43.3.0` can never satisfy it and the
  v2.3.1 build had never reached this line. Fixed by exact-pinning `electron` to `43.3.0`
  in `package.json`/`package-lock.json` (`npm ci` validates lock agreement; dist 43.3.0
  arm64 refetched and verified).
- DMG step: intentionally not exercised on the fix branch; the release DMG is
  built from the tagged commit after CI green, per the release discipline.

## TDD accounting

The behavior under change is the lockfile content plus the packaging contract;
the existing drift tests (`tests/test_headless_requirements_lock_drift.py`)
and packaging metadata tests pin both. They were run RED-adjacent (the
metadata/doc tests failed against the bumped version before their pin updates)
and are green with the restored lock, so the change is fully test-pinned.

## Review budget

`git diff --stat`: 19 files, +819/−491 raw. Generated-artifact noise
(`uv.lock` +328/−196 re-hash, `package-lock.json` version fields) accounts for
the bulk; hand-reviewed surface is 4 docs + 2 version pins + 1 test pin.
Within the 400-line hand-review budget; raw diff documented in the PR body.

## Residual risks

- `uv pip compile` without `--python-version 3.12` on a 3.11 host still fails;
  documented in `packaging/linux/README.md` and
  `docs/third-party-license-inventory.md` so the next regen is unambiguous.
- The DMG ceremony from the tagged commit re-runs gate + seal + freeze; a
  failure there would be a new root cause, not this one.
