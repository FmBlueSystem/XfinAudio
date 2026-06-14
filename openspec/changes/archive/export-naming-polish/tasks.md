# Tasks: Export Naming Polish

## Task 1 — Create naming utility

- [ ] Create `src/xfinaudio/exporting/export_naming.py`.
- [ ] Implement `default_export_filename(recommendation, generated_at=None, suffix=None)`.
- [ ] Sanitize output to be filesystem-safe.

## Task 2 — Update ExportCoordinator

- [ ] Replace `"XfinAudio Export"` fallback with `default_export_filename`.
- [ ] Apply to both `preview_non_serato_export` and `export_recommendation_to_non_serato`.
- [ ] Pass the same name as `playlist_name`.

## Task 3 — Add tests

- [ ] Create `tests/test_export_naming.py`.
- [ ] Assert timestamp, strategy, track count, and filesystem safety.

## Task 4 — Update related tests

- [ ] Update `tests/test_export_coordinator.py` if it asserts default filenames.

## Task 5 — Verify

- [ ] Run focused and full pytest suites.
- [ ] Run pyright, coverage, ruff check/format.
- [ ] Run `scripts/release_gate_check.py --run`.
