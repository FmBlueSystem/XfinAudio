# Design
Add an optional immutable ReplacementPolicy snapshot to PlaylistRecommendation:
resolved energy value, active normalized genre (None records fallback), one
bound color anchor's path/energy/profile, and the requested loudness band.
Capture at the actual filter stages before sequencing/trimming. No full library
or raw track metadata is retained; serialization/model_copy preserve the snapshot.
Use existing shared range/color/energy predicates at the pure replacement seam.
Optional additive lock/exclusion path sets let desktop pass current exceptions
without replacing the original policy. Desktop delegates raw candidates to this
single gate instead of re-resolving anchors over a changed library/settings.
Legacy context-dependent recommendations fail closed, rather than guessing.

Integration preserves the pre-existing current-settings desktop contract by
passing an explicit optional loudness override to the pure helper. It replaces
only the saved band in an existing policy snapshot. Legacy loudness-only edits
can use an explicit band, but other missing anchor context still fails closed.
