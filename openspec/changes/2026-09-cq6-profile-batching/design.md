# Design

## Baseline and constraints
CQ6 currently copies both library collections and searches the list per result;
spectral delivery then linearly inspects Qt Path items. Existing 200 ms render
coalescing cannot remove this earlier work. Measure baseline independently using
synthetic records, actual transition/controller paths, operation counts, and Qt
timer heartbeat delay at 1k/10k/50k. Separate table setup from result replay.

## Changes
- Add one pure batch transition: accumulate field updates keyed by path, copy
  the keyed store once, replace each changed immutable TrackRecord once, and
  reconstruct the existing ordered list in one pass. Retain single-result APIs
  for compatibility; do not change AppState's public schema.
- A parent-owned single-shot Qt timer queues controller result/profile progress
  changes. A flush publishes one immutable snapshot and requests one coalesced
  render, paints changed spectral cells directly, and refreshes loudness detail.
- Flush received work before terminal lifecycle transitions/context replacement;
  stopped timers must not leave callbacks that can contaminate a new library.
- Add a small lazy path-row index over QTableWidget. Structural/model layout
  changes and Path-cell edits invalidate it; Color-cell updates do not. Native
  sort, screen rebuild, row removal, hidden search rows, and quick-filter subset
  rebuilds stay correct. No QAbstractTableModel migration.

## Ownership and integration
app_state_transitions.py, library_controller.py completion paths, a dedicated
row-index helper, related focused tests, and this change's SDD artifacts. Shared
state correctness/lifecycle fixes belong to the parent integration tranche.
Workers already persist before emitting results; batching changes UI publication
only and must not touch their repository calls or serialization contracts.
