# Design: Review Layout Distribution + Unified Export Gate

## R1 — Review QSplitter

In `review_screen.py::_build_ui`, wrap the three section areas in a vertical `QSplitter`
(`self.tables_splitter`):
- Section 1 widget: `recommendation_table` + the actions row (remove/save).
- Section 2 widget: `transition_help_label` + `transition_table`.
- Section 3 widget: `readiness_table`.
Add the splitter to the root layout with stretch `1`; remove the trailing `addStretch(1)` that
competed for space. Set `setStretchFactor` so section 1 gets the largest share (e.g. 3/2/2) and
`setChildrenCollapsible(False)`. Table attributes remain accessible as before (no test breakage).

## R2 — history_table min/max

The compact override in `main_window.py` sets `history_table.setMaximumHeight(92)` while
`export_screen.py` sets `setMinimumHeight(200)`. Fix by having the compact override also lower the
minimum to match (`setMinimumHeight(min(current_min, max))`), so `min <= max` always holds. The
non-compact path keeps the 200 minimum.

## R3 — Unified export gate

Add a module-level `export_allowed(state: AppState) -> bool` in `navigation_controller.py`
(neutral, already imports `AppState`, imported by nobody it would cycle with):

```
def export_allowed(state):
    if state.is_recommending: return False
    if state.last_recommendation is None: return False
    remaining = [t for t in state.last_recommendation.ordered_tracks
                 if t.path not in state.playlist_removed_paths]
    if not remaining: return False
    report = state.last_dj_readiness_report
    return not (report is not None and report.status == "blocked")
```

Then:
- `NavigationController.can_go_to("export")` returns `export_allowed(state)`.
- `ReviewViewModel.can_export` returns `export_allowed(state)`.
- `ExportViewModel.export_enabled` returns `export_allowed(state)`.

This makes the report-present requirement uniform (report missing → allowed, matching the view
models) and folds the all-removed guard into the single predicate.

## Safety

- Pure UI/view-model layout and gating; no audio, DSP, or Serato writes.
- View models importing `navigation_controller` introduces no cycle (nav imports only `app_state`).

## Test strategy

- Offscreen Qt: assert `isinstance(screen.tables_splitter, QSplitter)` contains the 3 tables.
- Compact layout test: `history_table.minimumHeight() <= maximumHeight()`.
- Parity test: across representative states, the three predicates agree (incl. report-None and
  all-removed cases).
