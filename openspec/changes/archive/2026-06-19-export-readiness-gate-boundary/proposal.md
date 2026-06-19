# Proposal: Export Readiness Gate Boundary

## Intent

Separate export readiness and gate decisions from `xfinaudio.desktop.export_coordinator` into a pure export/application boundary. The desktop layer should consume a decision or plan, not compute whether an export is allowed, what gate failed, or which readiness state applies. This continues responsibility separation while preserving current behavior and UI copy.

## Scope

### In Scope
- Define a non-desktop readiness/gate boundary for export eligibility decisions.
- Update desktop export coordination to consume the boundary output while keeping widget orchestration in desktop code.
- Extend `export-planning` requirements so export planning includes readiness/gate decision ownership outside desktop.

### Out of Scope
- Export writer format changes.
- Serato DB V2 writes.
- UI redesign, copy changes, or dialog flow changes.
- Audio mutation, DSP, waveform analysis, rendering, mixing, time-stretching, or pitch-shifting.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `export-planning`: clarify that readiness/gate decisions are provided by a non-desktop boundary and consumed by desktop export coordination.

## Approach

Introduce or reuse a pure export/application-level component that evaluates export readiness from existing state/request inputs and returns a deterministic decision/plan. `xfinaudio.desktop.export_coordinator` remains responsible for widget state, folder dialogs, confirmation dialogs, status/error rendering, and invoking export use cases. Tests should first characterize current gate behavior, then verify the decision logic without PySide dependencies and the desktop consumption path without changing user-visible copy.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/export_coordinator.py` | Modified | Stop owning readiness/gate decision logic; consume boundary result. |
| `src/xfinaudio/application/` or `src/xfinaudio/exporting/` | Modified | Host pure export readiness/gate boundary. |
| `tests/` | Modified | Add RED/GREEN coverage for pure decisions and desktop consumption. |
| `openspec/specs/export-planning/spec.md` | Modified | Extend capability contract for readiness/gate ownership. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| UI copy or dialog behavior changes accidentally. | Medium | Characterization tests assert unchanged desktop-facing messages and flow. |
| Boundary duplicates export planning concepts. | Low | Keep it focused on readiness/gate decisions and delegate file planning to existing planner. |
| Refactor exceeds review budget. | Medium | Keep the slice limited to the gate boundary; defer broader export cleanup. |

## Rollback Plan

Revert the change folder and implementation diff. Because behavior and export formats are preserved, rollback restores the desktop-owned gate logic without data migration.

## Dependencies

- Existing `export-planning` capability.
- Existing desktop export coordinator behavior.

## Success Criteria

- [ ] Export readiness/gate decisions are testable without importing PySide desktop modules.
- [ ] Desktop export coordination consumes the decision/plan and keeps current UI copy and behavior.
- [ ] `export-planning` spec clearly assigns readiness/gate ownership to a non-desktop boundary.
