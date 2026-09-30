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

Slice 3 RED: styled Editor buttons were narrower than their size hints; Live
history left half the table unused; existing tooltip coverage failed. A second
geometry assertion caught button overflow into the cell's styled padding even
after a minimum-width attempt. GREEN: action item size hints now include the
style-reported cell insets and row height, so the whole button fits. History
stretches Title/Artist and sizes compact fields to content; current track names
wrap instead of raising the minimum width. Tooltips explain every Editor and
My Playlists action. A large-Library assertion also exposed unnecessary scrolling
at 1440×1000: controls now share available height with the track table.

Final focused verification: 191 tests pass; touched-file Ruff, formatting and
Pyright checks pass. No full gate run here (parent integrates it).
