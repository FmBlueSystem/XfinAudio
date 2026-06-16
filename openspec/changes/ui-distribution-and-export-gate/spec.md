# Specification: Review Layout Distribution + Unified Export Gate

## Requirements

### R1. Review tables are user-resizable

**GIVEN** the Review screen
**THEN** `recommendation_table`, `transition_table`, and `readiness_table` are children of a single
vertical `QSplitter`
**AND** the recommendation table receives the largest initial stretch share.

### R2. No contradictory history-table height

**GIVEN** the compact macOS layout is applied
**WHEN** the export `history_table` height constraints are set
**THEN** `minimumHeight() <= maximumHeight()` holds.

### R3. Single export-gate predicate

**GIVEN** any `AppState`
**WHEN** export permission is evaluated
**THEN** `NavigationController.can_go_to("export", state)`,
`ReviewViewModel.can_export(state)`, and `ExportViewModel.export_enabled(state)` return the same
boolean.

**GIVEN** a state with a recommendation but no readiness report
**THEN** all three permit export (no info → no block), removing the sidebar/Review dead-end.

**GIVEN** a state whose recommendation has all tracks removed
**THEN** all three deny export.

## Non-functional

- No regressions in existing desktop UI tests.
- Offscreen-Qt compatible; strict TDD.
- Within the 400-line review budget.
