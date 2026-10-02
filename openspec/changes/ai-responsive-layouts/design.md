# Design

Use Qt scroll-area viewport minimums rather than letting expanded control
content become the MainWindow minimum. Preserve fixed bottom navigation and
existing table stretch. Split Review's over-wide action row. Library upper
controls scroll independently from its track table and loudness details.
Create uses an adaptive controls budget and reveals actionable results.
Editor accounts for embedded button size hints; Live stretches text columns.

Tests construct a real shown MainWindow using isolated settings and synthetic
metadata, process Qt events, and assert actual geometry rather than size hints.
No data model or side-effect boundaries change. Full release gate belongs to
the integrating parent; this slice runs focused tests, lint and type checks.
