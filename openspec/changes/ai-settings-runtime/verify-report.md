# Verification report — 2026-09-30

## Result
Implementation and focused checks pass. The final integrated exact-commit release gate is pending and owned by the coordinator; this branch does not claim a full release-gate or live-provider pass.

## Requirement evidence
- R1: `test_ai_runtime_settings`, `test_ai_settings_dialog`, `test_ai_settings_controller`: default off, effective launcher settings, immutable candidates, persist-before-runtime enable/disable, cancellation, save failure. Four existing MainWindow startup tests also pass unchanged.
- R2: `test_ai_settings_panel`, `test_ai_connection_test`, `test_nan_error_redaction`: no key-entry field, only path persistence, no UI credential-file reads, environment precedence, no raw error leakage.
- R3: `test_ai_connection_test`, `test_nan_client`, `test_nan_transport_security`: exact synthetic payload, fixed safe statuses, key only in authorization header, no transport on disabled/missing/invalid setup, no redirect following, no raw provider content in status.
- R4: `test_ai_connection_probe`, `test_ai_settings_lifecycle`, `test_ai_settings_dialog`: background responsiveness, duplicates, retry, logical cancellation, stale results, Close/Cancel/deferred deletion with a running QThread, thread cleanup, focus/scroll and retained footer controls.
- Existing loudness settings/default/disclosure, settings persistence/recovery and adapter contracts remain covered.

## Commands and results
Shared interpreter: `/workspace/shared/xfinaudio/.venv/bin/python`, with `PYTHONPATH=src`.
- Focused pytest across all eight new test files plus existing adapter/security/settings/dialog/controller/recovery/repository files: **192 passed**.
- `pytest -q tests/test_main_window.py -k 'seed_ai_environment or seeds_the_ai_environment'`: **4 passed**.
- Ruff check and format-check over all 16 changed Python files: **passed**.
- Pyright over those files with `--pythonpath /workspace/shared/xfinaudio/.venv/bin/python`: **0 errors, 0 warnings**. The initial invocation without explicit interpreter could not resolve shared-venv dependencies; corrected invocation passed.
- Offscreen 720×640 Settings screenshot visually inspected after Configure AI focus: panel, privacy/test disclosures and footer actions visible. This is Linux/offscreen QA, not a macOS acceptance claim.

All API tests use synthetic credentials and injected transports. No real key or operator credential file was inspected, no live connection was made, and no dependencies, user-computer settings, audio files or Serato database were changed.

## Integration contract
- `SettingsController.open_ai_settings_dialog()` opens shared Settings and focuses the AI panel.
- `SettingsDialog.focus_ai()` schedules focus after layout.
- `apply_ai_settings(AiSettings)` runs after successful settings persistence; `effective_ai_settings(AiSettings)` reflects existing launcher overrides when opening.
- Keep the existing startup `seed_ai_environment` behavior to preserve explicit launcher precedence.
- Cancellation discards results and prevents a duplicate active probe; an already sent request may finish before retry is possible.
