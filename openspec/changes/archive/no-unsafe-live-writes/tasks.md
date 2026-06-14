# Tasks: No Unsafe Live Serato Writes

## Task 1 — Update Export screen copy

- [ ] Update `src/xfinaudio/desktop/export_view_model.py`:
  - `empty_state_text()` warns that live Serato writes are not part of the verified RC.
  - `destination_text()` clarifies exports go to the safe export folder and must be manually copied to a live library.
- [ ] Update `src/xfinaudio/desktop/screens/export_screen.py` default guidance label.

## Task 2 — Update release notes template

- [ ] Add a reinforced warning in `docs/release-notes-template.md` that live Serato writes are not part of the verified RC.

## Task 3 — Add tests

- [ ] Create `tests/test_export_view_model.py` asserting warning phrases.
- [ ] Create `tests/test_export_screen_copy.py` asserting guidance label warning (Qt offscreen).

## Task 4 — Verify

- [ ] Run focused and full pytest suites.
- [ ] Run pyright, coverage, ruff check/format.
- [ ] Run `scripts/release_gate_check.py --run`.
