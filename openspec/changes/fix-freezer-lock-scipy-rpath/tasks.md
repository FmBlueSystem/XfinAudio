# Tasks

- [x] Reproduce the audit failure on `ac4abd5` and capture the log (RED).
- [x] Regenerate `uv.lock` with `scipy==1.18.1`, `numpy==2.5.3`, `numba==0.68.0`, `llvmlite==0.50.0`.
- [x] Re-export `desktop-electron/requirements-headless.txt` from `uv.lock` (hash-locked, 33 pins).
- [x] Recompile `packaging/linux/requirements-build.txt`
      (`uv pip compile --generate-hashes --python-platform linux --python-version 3.12 packaging/linux/requirements-build.in -o packaging/linux/requirements-build.txt`).
- [x] Bump `pyproject.toml` version to 2.3.2; update release notes (2.3.1 = code-only, no DMG).
- [x] Drift tests green (8/8) + probe freeze passes `audit_tree` (GREEN — the check that
      failed on `ac4abd5`).
- [x] Full gate (`release_gate_check.py --run --report-json`) green on the fix branch:
      9/9 gates, 2,823 tests, coverage 91.81%, pyright 0, ruff/format PASS.
- [x] Exact-pin `desktop-electron` `devDependencies.electron` to `43.3.0` (latent
      `assemble` contract exposed by the probe; `npm ci` validates lock agreement).
- [ ] PR, CI green, merge; tag `v2.3.2` on main; DMG ceremony from the exact tagged commit.
