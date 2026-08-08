# Apply Progress: Phase 8 - Contextual Tooltips

## Completed

Shipped in commit `cb42989` (PR #61), "feat(ui): add contextual tooltips for all
controls". This file previously recorded only a `## Pending` placeholder while
`tasks.md` marked steps 2-6 done and `state.yaml` recorded apply and verify as
complete; it is rewritten here to record what the commit actually delivered.

- R1 — Button tooltips across the four workflow screens. `cb42989` added
  `setToolTip` calls to `screens/build_screen.py`, `screens/export_screen.py`,
  `screens/library_screen.py`, and `screens/review_screen.py`.
- R2 — Table column-header tooltips. Header items are now given tooltips at
  `screens/build_screen.py:192`, `screens/export_screen.py:186`, and
  `screens/review_screen.py:251`.
- R3 — "What's this?" help button. `LibraryScreen.build_help_dialog()` at
  `src/xfinaudio/desktop/screens/library_screen.py:95` returns the workflow help
  dialog, opened by the handler at `library_screen.py:121`.
- R4 — "Tour" walkthrough button. `LibraryScreen.tour_steps()` at
  `src/xfinaudio/desktop/screens/library_screen.py:108` supplies the ordered
  steps, shown by the handler at `library_screen.py:118`.
- Tests added by the same commit: `tests/test_build_screen.py`,
  `tests/test_export_screen.py`, `tests/test_library_screen.py`, and
  `tests/test_review_screen.py` (+93 test lines).

## Where the tooltips live today

The tooltip surface survived later refactors and grew beyond this change's
original four files. As of v1.7.7 the desktop package carries 47 `setToolTip`
calls across 16 modules, including `library_controller.py`,
`main_window_layout.py`, `table_populators.py`, `prep_copilot.py`,
`undo_toolbar.py`, and `window_service_wiring.py`.

The R3 help button and R4 tour button were later moved out of the screen class
into the builder: they are constructed at
`src/xfinaudio/desktop/library_screen_builder.py:165` (`screen.help_button`) and
`library_screen_builder.py:168` (`screen.tour_button`), while the dialog and
step logic stayed on `LibraryScreen`.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| R1 button tooltips | `tests/test_build_screen.py:60`, `tests/test_export_screen.py:49`, `tests/test_library_screen.py:208`, `tests/test_review_screen.py:8` — `test_all_buttons_have_tooltips` | UI unit | ✅ Existing screen suites | ✅ Failed on buttons with empty tooltips | ✅ All four screens pass | ✅ Every `QPushButton` found via `findChildren` | ✅ Per-screen tooltip maps |
| R2 header tooltips | `tests/test_build_screen.py:71` `test_copilot_table_headers_have_tooltips`, `tests/test_export_screen.py:60` `test_history_table_headers_have_tooltips`, `tests/test_review_screen.py:17` `test_recommendation_table_headers_have_tooltips` | UI unit | ✅ Existing screen suites | ✅ Failed on untooltipped header items | ✅ Three tables pass | ✅ Copilot, history, recommendation tables | ✅ Header tooltip loops |
| R3 help button | `tests/test_library_screen.py:219` `test_help_button_opens_help_dialog` | UI unit | ✅ Existing library screen suite | ✅ Failed before `build_help_dialog()` existed | ✅ Dialog returned with workflow text | — | ✅ Dialog construction split from handler |
| R4 tour button | `tests/test_library_screen.py:228` `test_tour_button_provides_walkthrough_steps` | UI unit | ✅ Existing library screen suite | ✅ Failed before `tour_steps()` existed | ✅ ≥3 ordered non-empty steps | — | ✅ Steps split from handler |

## Verification

Recorded in this change's `verify-report.md` at the time of the change:

- PASS: `uv run pytest -q` — 846 passed, 2 warnings.
- PASS: `uv run pyright src tests` — 0 errors.
- PASS: `uv run pytest --cov --cov-fail-under=70 -q` — 846 passed, coverage 89.19%.
- PASS: `uv run ruff check .`.
- PASS: `uv run ruff format --check .` — 190 files already formatted.
- PASS: `uv run python scripts/release_gate_check.py --run`.

## Files changed

- `src/xfinaudio/desktop/screens/build_screen.py` — button and header tooltips.
- `src/xfinaudio/desktop/screens/export_screen.py` — button and header tooltips.
- `src/xfinaudio/desktop/screens/library_screen.py` — button tooltips, help dialog, tour steps.
- `src/xfinaudio/desktop/screens/review_screen.py` — button and header tooltips.
- `tests/test_build_screen.py`, `tests/test_export_screen.py`, `tests/test_library_screen.py`, `tests/test_review_screen.py` — failing-first guard tests.

## Follow-up beyond this change

`tests/test_screen_tooltip_coverage.py` is a live parametrized guard asserting
that every `QPushButton` on seven screens carries a tooltip. It is **not** part
of this change: it was added later, in commit `9fb9e08` (2026-07-25), which
extended the R1 contract from the four screens covered here to `BuildScreen`,
`ExportScreen`, `LiveAssistantScreen`, `MetadataScreen`, `MyPlaylistsScreen`,
`PlaylistEditor`, and `ReviewScreen`. Its docstring records that 17 of 32
buttons carried a tooltip before that follow-up.

## Status

Implementation shipped and verified. `tasks.md` step 7 ("Commit and PR") is left
unchecked as the historical record; the commit and PR did land as `cb42989` /
PR #61.
