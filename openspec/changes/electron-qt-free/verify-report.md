# Verification: first vertical slice

Baseline: dd15f0dffb9d524169d9559e538e23afb23861a4. No push, merge or release.

- Strict TDD RED evidence: initial missing headless module, missing JS security module, renderer module and targeted regression failures recorded before their corresponding implementations. Host stream integration was also checked with subsequent regression tests.
- Python isolated headless environment: 23 focused backend/protocol tests passed
- Relevant existing application, recommendation, repository and scan tests plus new tests: 187 passed in a Qt-free environment with --noconftest
- Focused Python type check: 0 errors; Ruff lint/format passed
- npm build: strict TypeScript main and renderer compilation passed
- npm test with XFIN_PYTHON: 28 tests passed at final source checkpoint, including real subprocess scan/Prep/save/restart/audio-range workflow and mocked player controls
- npm audit: 0 reported vulnerabilities at lock creation
- Actual FLAC files are synthetic playable silence; fixture bytes remained unchanged
- Core import firewall verifies no Qt/desktop/provider imports; isolated runtime has no PySide6 distribution
- Native Electron binary reports 44.5.1, but GUI startup exits133 before app code with DBus socket Operation not permitted, including approved outside-command-sandbox attempt. No Electron sandbox was disabled.
- Cloud browser UI fallback rejects local file protocol under its policy. No visual screenshot or native decoding/output claim.
- Required aggregate legacy command attempted: uv run python scripts/release_gate_check.py --run --report-json /tmp/xfinaudio-electron-release-gate.json. Its prerequisite Qt install failed with No space left on device, so aggregate tests/type/lint/package checks did not run. Own reproducible cache copies were cleaned; no user files were removed.

Not release-ready. Native macOS arm64/UI/audio, package without system Python, full old-screen parity, stress/lifecycle and full aggregate gates remain open.

## First native feedback and v1 isolation update

- Native macOS arm64 programmatic smoke validation: synthetic tracks and 14 copied real files scan, balanced Prep, review/save/restart/open, muted FLAC play/pause/seek/resume/switch, sandbox enabled, no Qt loaded, clean exit 0, originals/copies unchanged. No human or audible-output/stress claim.
- Native unit fixture failed because /tmp resolves to /private/tmp; corrected only the fixture canonical root, preserving production path protection.
- RED→GREEN storage tests require Chromium userData/sessionData/logs/crashDumps to be set synchronously before readiness inside explicit XFIN_DATA_DIR. Native startup revalidation remains required for this delta.
- Linux npm test after these changes: 30 passed, including the real-core integration.
- Equivalent full Python verification: 3337 collected/tests passed in 22 fresh-process batches; combined coverage 94.29%. The initial split harness omitted the legacy venv from PATH for one packaging lookup and selected the wrong interpreter for Pyright; corrected reruns passed. Full Pyright 0 errors, Ruff lint/format 451 files pass, release-readiness smoke, source-package hygiene and PyInstaller check-only pass.
- The official monolithic aggregate was also retried with UV_NO_SYNC and the existing legacy environment: tests exited 137 around 50%; it is still not a green monolithic aggregate or release. No new Qt install in that retry.
