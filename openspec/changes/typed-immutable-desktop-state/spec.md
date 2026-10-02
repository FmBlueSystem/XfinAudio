# Observable requirements
- GIVEN a previously published snapshot WHEN a service changes scan/navigation/settings/selection fields THEN old snapshot fields remain unchanged and all rendering owners observe the new snapshot.
- GIVEN AppState WHEN a caller assigns a field directly THEN mutation is rejected; model_copy creates a distinct snapshot and rejects unknown field names.
- GIVEN legacy MainWindow property access WHEN a supported field is written THEN it publishes the replacement through the existing shell owner; reads have no hidden mutation side effects.
- GIVEN typed current-state/replacement access WHEN invalid getter, publisher or replacement-value contracts are supplied THEN targeted type checks reject them.
- GIVEN existing scan/recommendation/Prep/AI/filter/undo/export flows WHEN state changes THEN existing visible outcomes and worker safety remain unchanged.
Collection payloads remain structurally shared where unchanged; production code must never mutate published collections in place. This slice is field immutability, not a full persistent-collection conversion.
