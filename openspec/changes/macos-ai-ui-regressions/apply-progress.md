# Apply progress

- Baseline Linux: the two macOS CI failures did not reproduce directly.
- RED before production edits: 4 failures, 13 passes. Return/Enter leaked to the
  parent, a real mouse double-click emitted twice, and empty status was visible.
- GREEN: a list-local key handler owns Return/Enter and suppresses autorepeat;
  other keys still reach Qt. Only canonical itemActivated opens the set.
- GREEN: Review narrator status derives visibility from text, including existing
  controller updates. Clearing text restores the row height to all three tables.
- REFACTOR: retained existing signals, controller APIs and table-space assertions.
- VERIFY: 85 focused tests pass, including both keys through shell open, preview,
  apply, save and back. Changed Python files pass lint and format checks.
- Inspected actual Linux offscreen Review pixels at 1200x660 and 1000x700, idle
  and nonempty status. No clipping. Idle tables total 454/479px respectively.
- Full release gate passed: 3,246 tests / 94.28% coverage, every stage green.
  Native macOS rerun remains coordinator-owned.
