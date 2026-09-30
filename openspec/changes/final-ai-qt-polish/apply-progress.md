# Apply progress

2026-09-30: proposal, specification, design and task gates completed. Production
changes await failing regressions. Three bounded commits planned.

Slice 1 RED: all 8 direct lifecycle tests failed on missing attributes/deleted Qt
objects before production changes. GREEN: guarded incomplete/deleted children,
bound zero-delay callbacks to the screen QObject lifetime.

Slice 2 RED: 3 real-click regressions reproduced misleading cancellation on
Library Apply, Editor dismiss and local preview replacement. GREEN: completed
results are invalidated with neutral local-work guidance; active cancellation
retains its data-recall warning. Existing preview identity protection remains.
