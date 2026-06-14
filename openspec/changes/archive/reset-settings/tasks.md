# Tasks: Reset Settings

## Task 1 — SettingsDialog reset action

- [ ] Add a "Reset to Defaults" button to `SettingsDialog`.
- [ ] Show a confirmation `QMessageBox` on click.
- [ ] Emit `settings_changed` with `AppSettings()` and close the dialog if confirmed.

## Task 2 — SettingsController reset method

- [ ] Add `reset_to_defaults()` convenience method.
- [ ] Reuse existing `apply()` logic for persistence and UI refresh.

## Task 3 — Add tests

- [ ] Create `tests/test_settings_controller.py` and verify reset applies defaults.
- [ ] Create `tests/test_settings_dialog.py` and verify reset button and signal.

## Task 4 — Verify

- [ ] Run focused and full pytest suites.
- [ ] Run pyright, coverage, ruff check/format.
- [ ] Run `scripts/release_gate_check.py --run`.
