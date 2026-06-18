# Design: Hidden Bug Hardening

## Approach

- Move BPM validation to the final recommended order so the optimizer can find valid bridge tracks before any pruning occurs.
- Keep selected start constraints intact and make dropped end constraints explicit in warnings and applied controls.
- Treat visible table selection as the source of truth after filters; clear stale paths/constraints on folder changes.
- Wire `PlaylistWorkflowService` with an optional enrichment-service factory so desktop scans use current settings at scan time.
- Preserve hidden genre settings via `model_copy(update=...)` instead of rebuilding `GenreEnrichmentSettings` from UI fields only.
- Use `None` internally for transient provider failures; cache only successful `list` results.

## Safety

- All changes are metadata/UI/control-flow only.
- No audio files are written.
- No Serato live database writes are introduced.
- Runtime provider data remains per-user cache only.
