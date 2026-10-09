# Apply progress — fix-freezer-lock-scipy-rpath

## Phase: apply (2026-10-08)

- RED reproduced on `ac4abd5`: `packaging/macos/build.py` failed at
  `dependencies.py` L131 with `Runtime rpath escapes bundle`; offender
  `/tmp/xfin-231-build/core-dist/xfinaudio-core/_internal/libgfortran.5.dylib`
  (byte-identical processed copy of scipy 1.17.1's wheel dylib, flattened to
  `_internal/` top level with the wheel's 2-level rpath).
- Root cause verified: scipy 1.17.1 mac arm64 wheel ships
  `scipy/.dylibs/libgfortran.5.dylib` with absolute install id
  `/DLC/scipy/.dylibs/libgfortran.5.dylib`; PyInstaller 6.20.0 rewrites deps to
  `@rpath` plus one `..` per parent of the planned destination, so the flattened
  copy escapes `_internal/`. Precedent: 2.2.0 froze audit-clean with
  scipy 1.18.1 / numpy 2.5.3 / numba 0.68.0 / llvmlite 0.50.0 under the same
  PyInstaller version.
- Feasibility probe (`/tmp/lockprobe`): `uv lock --upgrade-package` per package
  resolves cleanly with librosa 0.11.0 unchanged.
- Applied: regenerated `uv.lock`, re-exported
  `desktop-electron/requirements-headless.txt` (exact documented `uv export`
  command), recompiled `packaging/linux/requirements-build.txt` with the
  documented command plus explicit `--python-version 3.12` (a non-3.12 default
  interpreter rejects `numpy==2.5.3`; docs updated with the flag).
- Semantic pin diff is exactly the four restored versions; the rest of the raw
  diff is hash reordering in generated artifacts.
- Version 2.3.2 applied across `pyproject.toml`, `uv.lock`,
  `desktop-electron/package.json`, `package-lock.json`, renderer version pill,
  and the pinned candidate version in
  `tests/test_electron_candidate_metadata.py`.
- Documentation updated: 2.3.1 notes marked code-only, new
  `docs/release-notes-v2.3.2.md`, license inventory version cells, README
  candidate paragraphs and notes links.
- Lock consistency: `tests/test_headless_requirements_lock_drift.py` 8/8 green
  on the regenerated locks.

## Phase: verify

See `verify-report.md`.
