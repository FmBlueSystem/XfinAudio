# Tasks: Scan Settings Review

## Task 1 — ViewModel method

- [ ] Add `scan_settings_review_text(state: AppState) -> str` to `LibraryViewModel`.
- [ ] Include supported extensions and required field mappings.

## Task 2 — Library screen label

- [ ] Add `scan_settings_label` QLabel to `LibraryScreen`.
- [ ] Update it in `render()` from the ViewModel method.

## Task 3 — Render wiring

- [ ] Confirm `MainWindow` re-renders the Library screen when the selected folder changes.

## Task 4 — Tests

- [ ] Add `tests/test_library_view_model.py` assertions for review text.
- [ ] Add `tests/test_library_screen.py` assertion for label text.

## Task 5 — Verify

- [ ] Run focused and full pytest suites.
- [ ] Run pyright, coverage, ruff check/format.
- [ ] Run `scripts/release_gate_check.py --run`.
