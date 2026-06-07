# Design: XfinAudio DJ QA Remediation

## Technical Approach

This change improves XfinAudio through small, reviewable, TDD-first slices. The architecture remains deterministic and metadata-first: recommendation and export safety rules live in pure modules where possible; PySide6 screens render view-model state and user guidance; `MainWindow` coordinates workflow and guards unsafe transitions.

Implementation order:

1. Restore clean quality gates.
2. Fix recommendation strategy correctness.
3. Fix candidate pool ordering before optimization.
4. Guard Serato export when readiness is blocked.
5. Align public widget aliases with visible widgets.
6. Improve Build, Review, Export, and Metadata guidance.
7. Record final QA evidence.

## Architecture Decisions

### Decision: Block blocked-readiness export in the first slice

**Choice**: Prevent crate writing when DJ readiness is `blocked`; keep preview enabled.
**Alternatives considered**: Allow override with confirmation; allow export but warn; only write sidecars.
**Rationale**: The current bug is product authority. A blocked recommendation should not silently write a Serato crate. Override can be added later only with explicit spec, UX copy, audit behavior, and tests.

### Decision: Keep recommendation fixes outside Qt first

**Choice**: Implement `same_energy` filtering in recommendation service and candidate ranking in recommendation presenter before UI polish.
**Alternatives considered**: Patch UI warnings only; add more controls; widen into audio analysis.
**Rationale**: UI can only explain the result; it cannot compensate for unsafe candidate selection. The product needs correct deterministic behavior before presentation improvements.

### Decision: Preserve DJ-controlled intent

**Choice**: Generated candidates obey strategy tolerance; explicitly controlled paths remain under DJ authority unless excluded.
**Alternatives considered**: Strictly filter all tracks including manual prefix/locked tracks.
**Rationale**: XfinAudio assists the DJ; it must not silently remove explicit operator choices. It should warn clearly when controlled choices create risks.

### Decision: Use view models for guidance copy

**Choice**: Add decision and empty-state copy through view models where possible, then render in screens.
**Alternatives considered**: Hard-code all copy directly in PySide6 widgets.
**Rationale**: View-model copy is easier to test without relying on display rendering, and keeps UI state observable.

### Decision: Use chained PRs

**Choice**: Treat this as a chained PR sequence because estimated changed lines exceed the 400-line review budget.
**Alternatives considered**: One large PR with `size:exception`.
**Rationale**: The change spans algorithms, export safety, UI state, tests, and QA scripts. Small PRs protect reviewer cognition and rollback control.

## Data Flow

Recommendation path:

```text
Library selection
  -> DJControls(start_path / locks / excludes)
  -> recommendation pool ranking by BPM/key/tag/energy/path
  -> playlist_service strategy filtering
  -> transition scoring and warnings
  -> Build summary / Review decision / Export readiness
```

Export path:

```text
Recommendation result
  -> DJ readiness report
  -> Export view model
       ├─ preview allowed even when blocked
       └─ crate write disabled when blocked
  -> defensive MainWindow export guard
  -> Serato crate writer only when allowed
```

QA path:

```text
pytest + ruff + format
  -> release_gate_check
  -> controlled temp Serato E2E
  -> screenshot/manual visual inspection
  -> verify-report.md
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/main_window.py` | Modify | Lint cleanup, export guard, visible table alias cleanup, workflow wiring. |
| `src/xfinaudio/desktop/recommendation_presenter.py` | Modify | Candidate pool ranking uses BPM feasibility before generic tag count. |
| `src/xfinaudio/recommendation/playlist_service.py` | Modify | Enforce `same_energy` energy tolerance around anchor. |
| `src/xfinaudio/desktop/build_view_model.py` | Modify | Build guidance, anchor summary, recommendation summary state. |
| `src/xfinaudio/desktop/review_view_model.py` | Modify | Decision banner state and copy. |
| `src/xfinaudio/desktop/export_view_model.py` | Modify | Export empty state and blocked export guidance. |
| `src/xfinaudio/desktop/metadata_view_model.py` | Modify | Metadata repair-loop empty/help state. |
| `src/xfinaudio/desktop/screens/build_screen.py` | Modify | Render Build guidance and empty/summary state. |
| `src/xfinaudio/desktop/screens/review_screen.py` | Modify | Render decision-first Review layout. |
| `src/xfinaudio/desktop/screens/export_screen.py` | Modify | Render export guidance and disabled action state. |
| `src/xfinaudio/desktop/screens/metadata_screen.py` | Modify | Render metadata worklist guidance. |
| `tests/test_playlist_strategies.py` | Modify | RED/GREEN coverage for `same_energy` filtering. |
| `tests/test_recommendation_presenter.py` | Modify | RED/GREEN coverage for BPM-feasible pool ranking. |
| `tests/test_main_window.py` | Modify | Export block and table alias coverage. |
| `tests/test_build_view_model.py` | Modify | Build guidance coverage. |
| `tests/test_review_view_model.py` | Modify | Review decision copy coverage. |
| `tests/test_export_view_model.py` | Modify | Export empty/blocked state coverage. |
| `tests/test_metadata_view_model.py` | Modify | Metadata repair-loop coverage. |
| `tests/test_visual_integration.py` | Modify | Visible widget/table and UI integration coverage. |
| `tests/integration_flow.py` | Modify | Lint/format cleanup and visible widget assertions. |
| `scripts/manual_desktop_qa.py` | Create/Modify | Optional reusable controlled manual QA harness. |
| `scripts/capture_desktop_screens.py` | Create/Modify | Optional screenshot evidence harness. |

## Interfaces / Contracts

### Same-energy strategy contract

```python
# Generated candidates must satisfy:
anchor_energy - strategy.energy_tolerance <= candidate.energy_level <= anchor_energy + strategy.energy_tolerance
```

Controlled paths are preserved unless excluded, and warnings describe any tolerance filtering or missing metadata.

### Export safety contract

```text
readiness.status == "blocked" -> crate write disabled and defensively blocked
readiness.status == "blocked" -> preview remains enabled and writes no files
```

### Visible table contract

```python
window.tracks_table is window._library_screen.tracks_table
```

If this exact alias is impossible, a replacement visible-widget accessor must be named, documented, and tested.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `same_energy` tolerance | Failing strategy test before implementation. |
| Unit | Pool ranking | Failing presenter test with 102 BPM anchor and 103 vs 126 BPM candidates. |
| Unit/View model | Build, Review, Export, Metadata guidance | Test user-observable strings/state without display rendering. |
| Qt/offscreen | Export block and table alias | `tests/test_main_window.py` and visual integration tests. |
| Integration | Full desktop flow | Controlled temp Serato export path, no real library writes. |
| QA | Screenshots and manual review | Capture evidence and inspect primary action/decision clarity. |

## Migration / Rollout

No data migration required. Roll out through chained PR slices:

1. Quality baseline.
2. Recommendation correctness.
3. Export safety.
4. Widget truthfulness.
5. UX guidance.
6. Final QA evidence.

## Open Questions

- [ ] Chain strategy must be selected before apply: `stacked-to-main` or `feature-branch-chain`.
- [ ] Export override is intentionally not implemented in the first slice; if required, create a separate spec.
- [ ] Minimum useful playlist length for real DJ workflow should be confirmed during manual QA.
