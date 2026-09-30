# Scenarios

- Given a finite result under 60 seconds, retain valid LUFS and true peak as partial, omit LRA, and do not write the complete three-metric comment.
- At 60 seconds, permit all finite valid metrics. Stability is not a promise of universal conformance.
- Reject undefined integrated floor (-70 LUFS), nonfinite numbers, negative LRA and invalid duration as complete measurements.
- Old analysis/tag versions cannot be recovered, displayed or selected as current complete measurements.
- Current complete measurements still write the approved comment normally.
- Synthetic known-level, gate and intersample signals must satisfy published reference tolerances.
