# Design: Auto-save Playlist on Export

## Decision question

Where should the auto-save hook live so that it only triggers on successful export, not on preview?

## Alternatives considered (Arbor-style)

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Hook in `ExportCoordinator.export_recommendation_to_serato` after a successful write | Single hook point; clear precondition. | Couples export coordinator to playlist coordinator. | **Selected.** |
| B. Hook in `MainWindow._on_export_recommendation` at the call site | UI-level; easy to disable. | Bypasses coordinator abstraction. | Rejected. |
| C. Use an event bus / signal | Decoupled. | Over-engineered for one call. | Rejected. |

## Architecture impact

- `PlaylistCoordinator.save_recommendation` is reused; add an optional `auto=True` mode that uses a timestamped default name.
- `ExportCoordinator` gets a reference to `PlaylistCoordinator` (or a `save_recommendation` callable) and calls it after a successful export.

## Affected files

- `src/xfinaudio/desktop/export_coordinator.py`
- `src/xfinaudio/desktop/main_window.py` (wire the new dependency)
- `tests/test_export_coordinator.py`

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato Database V2 writes (the actual export already does that, unchanged).
