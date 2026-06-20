# Recommendation Candidate Application Boundary

Move interactive recommendation candidate-pool planning behind an application-layer boundary so desktop UI does not call recommendation policy modules directly.

In scope: application candidate-pool request/result boundary, desktop delegation from `MainWindow`, focused tests, SDD evidence.
Out of scope: changing recommendation scoring semantics, DSP/audio mutation, export formats, live Serato DB V2 writes.

Success: `desktop.main_window` no longer imports `build_recommendation_pool` from recommendation internals; application tests prove candidate pool behavior is preserved.
