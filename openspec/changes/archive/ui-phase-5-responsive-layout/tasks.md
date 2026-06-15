# Tasks: Phase 5 - Responsive Layout

## Review Workload Forecast

- 400-line budget risk: Low
- Chained PRs recommended: No
- Decision needed before apply: No
- Estimated changed lines: ~150 (within the 200-line review budget)

## Tasks

1. [x] Proposal, spec, design (authored in apply — see deviation note)
2. [x] Add `WindowSettings` model to `settings.py` and wire into `AppSettings`
3. [x] Add `responsive_sidebar_width` pure function + breakpoint constants
4. [x] Apply width-driven sidebar sizing + icon-only collapse via `resizeEvent`
5. [x] Add `set_full_screen` toggle (hide/show sidebar + status controls)
6. [x] Restore window geometry in constructor; persist on `closeEvent`
7. [x] Focused tests (RED → GREEN) in `test_main_window.py` + `test_settings.py`
8. [x] Verify (full suite, pyright, coverage, ruff, release gate)
9. [ ] Commit and PR

## Notes

- `library_screen.py` requires no structural change: the responsive sidebar is
  owned by `MainWindow`, not `LibraryScreen`. Listed-but-untouched per design.
