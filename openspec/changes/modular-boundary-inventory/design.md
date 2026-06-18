# Modular Boundary Inventory Design

## Architecture

This slice is intentionally narrow. It documents the full modular target but only extracts one low-risk policy: recommendation candidate-pool selection. The policy has no Qt dependency, so moving it from `xfinaudio.desktop` to `xfinaudio.recommendation` improves boundaries without changing UI behavior.

## Target Module Groups

- `xfinaudio.library`: scan, persisted tracks, metadata completeness, library filters.
- `xfinaudio.recommendation`: strategy registry, candidate-pool policy, scoring, optimization, Prep Copilot planning.
- `xfinaudio.exporting`: export planning, safe-write behavior, sidecars, format writers.
- `xfinaudio.quality`: DJ readiness and recommendation quality reports.
- `xfinaudio.config`: settings models and persistence.
- `xfinaudio.desktop`: PySide6 widgets, signal wiring, rendering, and user interaction only.

## Files

- Create `docs/architecture/functional-inventory.md` for the inventory.
- Create `src/xfinaudio/recommendation/candidate_pool.py` for pure candidate-pool policy.
- Keep `src/xfinaudio/desktop/recommendation_presenter.py` as a compatibility wrapper during this slice.
- Extend `src/xfinaudio/recommendation/strategies.py` with a pure resolver for internal names/display labels.
- Update desktop imports to consume the non-UI module.
- Add focused unit tests under `tests/`.

## Safety

No audio files are mutated. No DSP scope is added. No live Serato database V2 writes are introduced. The slice stays below the 400-line review budget where possible.
