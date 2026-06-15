# Apply Progress: Phase 4 - Visual Hierarchy

## Status

Apply complete — verified.

## Completed

- `theme.py`: added `QPushButton#secondaryAction` (muted, smaller) and `QFrame#sectionDivider`
  styles; enlarged `#primaryAction` and `#seratoExportButton` padding/font for primary emphasis.
- Library: `scan_button` → `primaryAction` (min-height 36); `cancel_button`/`settings_button`
  → `secondaryAction` (max-height 26); `section_divider` `QFrame.HLine`; `empty_state_label`
  for no-library and no-tracks states driven from `state.selected_folder`/`state.scanned_records`.
- Build: `recommend_button` → `primaryAction`; `back_button` → `secondaryAction`;
  `section_divider`; `empty_state_label` for no-recommendation (`state.last_recommendation is None`).
- Export: `preview_button`/`back_button` → `secondaryAction`; `export_button` kept
  `seratoExportButton` accent with larger min-height; `section_divider`.

## TDD Cycle Evidence

| Phase | Result |
|------|--------|
| RED | 8 new focused tests failed (missing objectNames/divider/empty-state); 7 baseline passing |
| GREEN | 15/15 focused tests passing; 833/833 full suite passing |
| Regression | `tests/test_main_window.py` 99 passed (no out-of-scope test broken) |

## Verification

- All seven required commands PASS (see `verify-report.md`).
