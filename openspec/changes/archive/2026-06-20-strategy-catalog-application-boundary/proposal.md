# Strategy Catalog Application Boundary

Move playlist strategy catalog lookup behind an application-layer boundary so desktop no longer reads private recommendation internals.

In scope: application strategy catalog DTOs/functions, BuildViewModel delegation, focused tests, SDD evidence.
Out of scope: changing strategy algorithms, names, weights, DSP/audio mutation, export formats, live Serato DB V2 writes.

Success: `desktop.build_view_model` no longer imports `_STRATEGIES` or `StrategyName`; UI behavior remains unchanged; full gates pass.
