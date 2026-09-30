# Apply progress

2026-09-30: Proposal/spec/design/tasks complete. RED tests are next.

Slice 1 RED: four actual-window regressions failed on baseline; compact
Library became 1133×777 and expanded Review 1133×848. GREEN: upper Library
controls scroll separately; Review uses two action rows and a scrollable body.
The Review body uses minimum height-for-width so wrapping labels do not turn
preferred table heights into mandatory scroll height. Existing table-space
and keyboard-detail tests remain green (53 focused tests).

Slice 2 RED: confirmation buttons were outside the viewport at both sizes;
recovery status and Configure AI were also clipped (corrected the test's
message expectation and reconfirmed both geometry failures on the old screen).
GREEN: controls share available height with variants instead of a fixed cap;
a deferred, change-sensitive reveal uses settled geometry for new recovery or
confirmation. Identical re-renders preserve manual scrolling. 43 focused
Create/responsive tests pass, including previous minimum table-space behavior.
Targeted Ruff/Pyright pass with the shared virtualenv explicitly selected.
