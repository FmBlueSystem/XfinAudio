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
