# Design: Project Audit Remediation

## Technical Approach

Remediate gates before structural work, then extract one characterized responsibility per feature-branch-chain slice. Public `MainWindow`, `LibraryScreen`, `ExportCoordinator`, `layout` imports, signals, and `AppState.model_copy(update=...)` semantics remain stable.

## Architecture Decisions

| Decision | Choice | Alternative | Rationale |
|---|---|---|---|
| Native startup seam | Add a small injectable macOS activation adapter called by `_configure_macos_app`; default adapter performs the lazy AppKit access | Skip macOS configuration in all tests | Tests avoid `NSApplication.sharedApplication()` while production behavior remains exercised through a fake adapter. |
| Dependency policy | Add compatible-major upper bounds and regenerate `uv.lock` | Exact-pin every direct dependency | Bounded ranges satisfy governance without preventing compatible patch/minor resolution. |
| Lifecycle repair | Reconcile active changes from existing artifacts and verification evidence; create missing reports/state without editing archives | Mark every stale change complete | Evidence, not file presence alone, determines status. |
| Module decomposition | Preserve existing facades and extract private collaborators | Rename/rewrite public coordinators | Limits blast radius and protects established tests/callers. |
| Delivery | Feature-branch chain; each slice ≤400 changed lines | One large PR | Moving code counts as additions plus deletions, so narrow extractions are required. |

## Extraction Boundaries

| Current module | New boundary | Retained contract |
|---|---|---|
| `screens/library_screen.py` | `library_screen_builder.py`: controls/table/footer construction and intrinsic accessibility configuration | `LibraryScreen` widgets, signals, labels, tab order |
| `screens/library_screen.py` | `library_table_presenter.py`: sort keys, row materialization, selection/playing/constraint painting | `render()`, row/path mapping, selection behavior |
| `screens/library_screen.py` | `library_filter_state.py`: query/quick-filter state and matching | Current button methods and emitted filter labels |
| `layout.py` | `main_window_layout.py`: sidebar/workflow composition, responsive widths, visibility helpers | `layout.py` re-exports and `MainWindow._build_layout()` |
| `layout.py` | `window_service_wiring.py`: scan/recommendation service wiring and restoration transitions | Existing `_layout.*` facade calls |
| `layout.py` | Keep thin compatibility delegates in `layout.py`; remove only proven-unreferenced duplicates | Existing import paths |
| `export_coordinator.py` | `software_export_coordinator.py`: non-Serato preview/export | `ExportCoordinator` public methods |
| `export_coordinator.py` | `serato_recommendation_export.py`: Serato plan/preview/write/readiness sidecars | Safe export, backup, gate, receipt behavior |
| `export_coordinator.py` | `serato_metadata_worklist_export.py`: status/missing-field worklists | Metadata messages and safe Serato flow |

## Flow

```text
MainWindow/Screen facade -> extracted collaborator -> existing application service
          state update <- result/status/receipt <- safe export or rendering path
```

No audio data is mutated. Serato writes continue through existing planning, backup, validation, and export services.

## Feature-Branch-Chain Work Units

| Slice | Scope | Budget |
|---|---|---|
| PR1 | RED startup isolation; adapter GREEN; dependency bounds + lock | ≤250 |
| PR2 | Reconcile active OpenSpec artifacts/state with evidence | ≤250 |
| PR3 | Extract library table presenter | ≤400 |
| PR4 | Extract library UI builder | ≤400 |
| PR5 | Extract library filter state | ≤300 |
| PR6 | Extract main-window layout composition | ≤400 |
| PR7 | Extract service wiring; retain layout facade | ≤350 |
| PR8 | Extract generic and Serato recommendation export collaborators | ≤400 |
| PR9 | Extract metadata worklist/history responsibilities | ≤350 |

Each child branch targets the preceding slice, runs focused tests plus full gates, and can be reverted independently.

## File Changes

Modify `app.py`, `test_desktop_app.py`, `pyproject.toml`, `uv.lock`, the three audited modules, their focused tests, and active `openspec/changes/*`. Create the collaborator modules listed above. Delete no public module.

## Interfaces / Contracts

Collaborators accept narrow structural hosts/callables. Facades retain current method signatures and Qt signals. No persisted-data migration or new dependency is introduced.

## Testing Strategy

| Layer | Coverage |
|---|---|
| Unit | Native adapter, dependency constraint audit, filter/sort/export collaborators |
| Qt integration | Widget identities, signals, table rows, navigation, layout |
| Safety/E2E | Export gates/backups/receipts and complete release gate |

Strict TDD applies per behavior slice: focused RED, minimal GREEN, REFACTOR, then the ordered project verification commands.

## Threat Matrix

| Boundary | Applicability |
|---|---|
| Documentation-like paths | N/A — no executable classification |
| Git repository selection | N/A — no VCS automation is implemented |
| Commit state | N/A — delivery branches do not alter commit tooling |
| Push state | N/A — no push automation |
| PR commands | N/A — chain targeting is a human/agent delivery convention, not command composition code |

## Migration / Rollout

No data migration. Roll out sequentially; revert the failing slice without reverting earlier verified slices.

## Open Questions

None.
