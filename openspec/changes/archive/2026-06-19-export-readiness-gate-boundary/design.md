# Design: Export Readiness Gate Boundary

## Technical Approach

Create a small pure export boundary in `src/xfinaudio/exporting/export_readiness.py` that evaluates whether the selected export action may continue. It will receive already-available desktop state as plain values and return a structured decision code. `ExportCoordinator` will translate those codes into the existing `host.tr(...)` strings and then continue to the existing file planner, Serato planner, and writers. The delta spec exists at `openspec/changes/export-readiness-gate-boundary/specs/export-planning/spec.md` and is the behavior source for this design.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Boundary location | Add `xfinaudio.exporting.export_readiness` | Put logic in `desktop` or a broad application service | `exporting` already hosts UI-independent planning (`playlist_file_export.py`); keeping this module pure prevents PySide/desktop coupling. |
| Return contract | Frozen dataclasses plus enum-like string codes such as `allowed`, `missing_recommendation`, `blocked_readiness`, `missing_safe_folder` | Return translated messages or raise exceptions for normal gate failures | Codes keep UI copy in desktop, are easy to unit test, and avoid using exceptions for expected state. |
| Software validation | Do not validate unknown software in the readiness gate | Add an `unknown_software` gate code | Current behavior reaches existing planner/writer handling after recommendation/safe-folder checks; preserving that flow avoids changing visible priority or error ownership. |
| Slice size | Extract only readiness/gate checks | Refactor all export planning/writing | The proposal asks for responsibility separation, not a full exporting rewrite; small scope protects the 400-line budget. |

## Data Flow

```text
ExportCoordinator
  └─ builds ExportGateRequest from host state
       └─ evaluate_export_gate(request)  [pure]
            ├─ denied(code) -> desktop maps code to existing UI copy and returns
            └─ allowed -> existing playlist/Serato planner and writer flow
```

Gate ordering must preserve current behavior:
1. Missing recommendation blocks preview/export for all software.
2. Blocked DJ readiness blocks export only, not preview.
3. Missing safe folder blocks non-Serato preview/export before planner validation.
4. Unknown software remains handled by `plan_playlist_file_export`/writer branch.

## File Changes

| File | Action | Description |
|---|---|---|
| `src/xfinaudio/exporting/export_readiness.py` | Create | Pure request/decision models and `evaluate_export_gate`. No `xfinaudio.desktop` or `PySide6` imports. |
| `src/xfinaudio/desktop/export_coordinator.py` | Modify | Build gate requests, map decision codes to existing messages, and keep existing planners/writers. |
| `tests/test_export_readiness.py` | Create | Unit tests for missing recommendation, blocked readiness, missing safe folder, allowed decisions, and unknown-software pass-through. |
| `tests/test_export_coordinator.py` | Modify | Desktop consumption/characterization tests for unchanged status copy and planner/writer short-circuiting. |
| `openspec/specs/export-planning/spec.md` | Modify later | Archive/merge the new requirement after verification, not during this design phase. |

## Interfaces / Contracts

```python
@dataclass(frozen=True)
class ExportGateRequest:
    operation: Literal["preview", "export"]
    software: str
    has_recommendation: bool
    readiness_status: str | None
    safe_folder: Path | None

@dataclass(frozen=True)
class ExportGateDecision:
    allowed: bool
    code: Literal["allowed", "missing_recommendation", "blocked_readiness", "missing_safe_folder"]
```

`evaluate_export_gate(request)` is deterministic and side-effect free. `software == "Serato"` does not require `safe_folder`; all other software values do, matching current non-Serato behavior without claiming software validity.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Pure decision ordering and codes | Add failing `tests/test_export_readiness.py` first. |
| Desktop | Message mapping and short-circuit behavior | Add/adjust `ExportCoordinator` tests with fake host and patched planners/writers. |
| Integration | Existing multi-software export still writes supported formats | Keep current tests; add only if a regression appears. |

## Migration / Rollout

No migration required. This is an internal boundary extraction with preserved UI copy and export formats.

## Open Questions

- [ ] None blocking.
