# Apply progress

2026-09-30: Read governance, inspected current Library/Create and established chain.
No implementation before SDD. Existing extraction sends titles; default transmission
will be narrowed. Existing controller generates immediately, so preview is a behavior
change and legacy lifecycle tests must explicitly confirm the new two-stage contract.

Slice 2 RED: test_library_query failed collection (new parser absent). GREEN:
9 parser/predicate cases pass with exact English/Spanish ranges, unsupported and
invalid constraints rejected, unknown metadata excluded, immutable records retained.

Slice 3 RED: both real-widget scenarios failed (query panel absent). GREEN: 11
parser/widget tests pass. QTest keyboard/clicks exercise local interpretation,
visible fields, edited range apply, invalid preservation, retry and clear.

Slice 3 follow-up: the initial 11 green assertions had a process-exit SIGSEGV,
not a clean pass; fixed the panel's owning-screen reference cycle using weakref.
Rerun exits 0. Real MainWindow callback RED exposed filter reset (2 rows vs 1).
GREEN keeps described filters and duplicate suppression through the callback;
12 focused tests now pass and process exits 0. Initial long-line lint fixed.
