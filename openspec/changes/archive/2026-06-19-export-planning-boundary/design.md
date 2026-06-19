# Export Planning Boundary Design

## Architecture
Create `xfinaudio.exporting.playlist_file_export` as a pure planning module. It owns only deterministic non-Serato file export decisions:

- supported software to file extension mapping;
- target-name precedence;
- target path construction;
- immutable plan value object.

`desktop.export_coordinator.ExportCoordinator` remains responsible for:

- reading UI/host state;
- translated status/guidance labels;
- writer dispatch and exception handling;
- Serato planning/writing and metadata worklist export.

## Data Model

```python
@dataclass(frozen=True)
class PlaylistFileExportPlan:
    software: str
    target_name: str
    target_path: Path
    playlist_name: str
```

## Safety
- No audio mutation.
- No DSP scope.
- No live Serato database V2 writes.
- No UI strings in the new exporting module.
- No file writes in the planner.

## Testing
Add `tests/test_playlist_file_export.py` with RED-first unit tests for the pure planner. Keep existing desktop/export integration tests as behavioral guardrails.
