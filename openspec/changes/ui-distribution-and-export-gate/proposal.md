# Proposal: Review Layout Distribution + Unified Export Gate

## Intent

Fix the highest-impact visual-distribution and flow defects found in a desktop UI audit, without
a UI rewrite. Scope is deliberately narrow and evidence-backed.

## Context and evidence (from UI audit)

- **Review screen**: `recommendation_table`, `transition_table`, `readiness_table` are each
  `Expanding/Expanding` and added with stretch `1`, plus a trailing `addStretch(1)` — four stretch
  consumers fight for vertical space, so all three tables stay cramped
  (`review_screen.py:135,169,179,182`).
- **Export history table contradiction**: `history_table` has `minimumHeight(200)`
  (`export_screen.py`) while the compact override sets `maximumHeight(92)`
  (`main_window.py:828`) — min > max, an undefined Qt constraint.
- **Export gate dead-end**: `NavigationController.can_go_to("export")` requires a readiness report
  to be present (`navigation_controller.py:32`), but `ReviewViewModel.can_export` and
  `ExportViewModel.export_enabled` allow export with no report. So Review's "Export →" works while
  the sidebar "Export" stays disabled for the same state — contradictory affordances.

## Scope

### In scope

- Review: place the three tables in a user-resizable vertical `QSplitter` with proportional initial
  sizes; remove the competing trailing stretch.
- Export: reconcile `history_table` min/max so the compact constraint is consistent.
- Export gate: a single source of truth `export_allowed(state)` used by the navigation controller
  and both view models, eliminating the dead-end.

### Out of scope

- BuildScreen label grouping, LiveAssistant margins, sidebar icons, persistent error banners
  (tracked as follow-ups).
- Any recommendation-engine or non-UI logic.

## Success criteria

1. The three Review tables live in a `QSplitter` and are user-resizable; the recommendation table
   gets the largest initial share.
2. `history_table` never has `minimumHeight > maximumHeight`.
3. `NavigationController.can_go_to("export")`, `ReviewViewModel.can_export`, and
   `ExportViewModel.export_enabled` agree for every state (single predicate).
4. All verification commands pass; no regressions in existing UI tests.

## Rollback plan

- Revert the three localized edits; each is independent.

## Review budget

~150 production + ~120 test lines, within the 400-line budget.
