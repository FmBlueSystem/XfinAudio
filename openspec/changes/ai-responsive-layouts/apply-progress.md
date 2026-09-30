# Apply progress

2026-09-30: Proposal/spec/design/tasks complete. RED tests are next.

Slice 1 RED: four actual-window regressions failed on baseline; compact
Library became 1133×777 and expanded Review 1133×848. GREEN: upper Library
controls scroll separately; Review uses two action rows and a scrollable body.
The Review body uses minimum height-for-width so wrapping labels do not turn
preferred table heights into mandatory scroll height. Existing table-space
and keyboard-detail tests remain green (53 focused tests).
