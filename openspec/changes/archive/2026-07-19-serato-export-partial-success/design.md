# Design: Serato Export Partial-Success Semantics

## Technical Approach

Converge every readiness-sidecar failure onto the graceful-degradation path that
already exists for `OSError`, without duplicating any of that path's logic. The
crate write (`serato_recommendation_export.py:161-181`) is unchanged and stays
committed to disk before the sidecar step begins; only the `except` boundary at
line 203 widens. The shared post-sidecar block (guidance label, status text,
`_record_serato_export`, callback suppression) already lives *after* the
try/except and keys off `readiness_paths == (None, None)` and `readiness_note`,
so broadening the caught type is the entire behavioral change — no new branch,
no copied handler.

Alongside the resilience fix, tighten the export dependency bundle: drop the
one collaborator no bundle consumer reads (`READ-005`) and replace the seven
`Callable[..., Any]` fields with statically checked contracts (`READ-006`).
Both are static-only edits that leave runtime behavior identical.

Public surfaces stay stable: `ExportCoordinator` construction/signatures, the
`SeratoRecommendationExportMixin` flow, the `write_readiness_sidecars` /
`plan_serato_export` compatibility entrypoints in `export_coordinator.py`, and
the direct `write_application_dj_readiness_report` import used by
`export_actions.py:55`.

## Architecture Decisions

| Decision | Choice | Rejected alternative | Rationale |
|---|---|---|---|
| RES-002 exception boundary | Widen `except OSError` at `serato_recommendation_export.py:203` to `except Exception as exc:`, keeping `LOGGER.exception(...)` and the existing `readiness_note` assignment; the shared post-sidecar block converges all failures | Add a second `except Exception` branch beside the `OSError` one | A second branch would duplicate the log + `readiness_note` assignment and risk divergence. One widened clause reuses the existing convergence point (`readiness_paths` stays `(None, None)` from line 189) with zero duplication. |
| KeyboardInterrupt / SystemExit handling | No explicit handling needed | Catch and re-raise `BaseException` subclasses, or use `except (Exception, ...)` gymnastics | `KeyboardInterrupt` and `SystemExit` derive from `BaseException`, not `Exception`, so `except Exception` never catches them — they propagate unchanged. This is the desired behavior: interrupts and interpreter exit must not degrade into a partial-success label. No extra code. |
| Crate-write re-entry | Crate write stays outside and before the sidecar try/except; the sidecar path only sets note/paths and never re-invokes the writer | Wrap crate write + sidecar in one try with retry | The crate is written once at lines 161-181 and is already committed when the sidecar step runs. A retry of sidecar generation touches only `write_readiness_sidecars`; it can never rewrite or corrupt the crate because the writer is not reachable from the sidecar boundary. |
| Callback policy on partial success | Suppress `self._on_export_success()` on **any** sidecar failure (uniform with today's `OSError` behavior at lines 223-226) | Fire the success callback because the crate succeeded | The callback signals a *complete* export (downstream navigation / history-refresh side effects imply full success). A missing readiness sidecar is a partial outcome; firing would misreport it. Suppression keeps the two failure types uniform and is asserted by test. The crate path is still reported and the receipt still recorded, so suppression loses no user information. |
| READ-005 removal scope | Remove `write_application_dj_readiness_report` only from `ExportDependencies` (field), `default_export_dependencies()` (deferred import + assignment), and the `export_coordinator.py:139` bundle constructor | Remove the function entirely, or route sidecar writing through the bundle field | The field has no attribute reader anywhere (verified: only construction sites). The function is still consumed directly — `export_actions.py:55`, and as the `write_report` default in both `write_readiness_sidecars` definitions (`serato_recommendation_export.py:85`, `export_coordinator.py:73`). Those direct uses and the `export_coordinator.__all__` re-export stay intact. |
| READ-006 contract style | One precise `Callable` alias for the single-positional gate, and `typing.Protocol` classes with `__call__` for the keyword-argument collaborators; reuse the existing `LibraryDiscoverer` alias for discovery | One broad `Protocol` per field with `*args, **kwargs`, or keep `Callable[..., Any]` | Matches the house pattern already set by `PlaylistFileWriter`, `SeratoCrateWriter`, and `LibraryDiscoverer`. Precise contracts let pyright catch call-site drift; `Callable[..., Any]` defeats that. Keyword-only call sites require `Protocol.__call__` because `Callable[[...], R]` cannot express keyword-only parameters. |
| READ-006 import strategy | Import the referenced types under `if TYPE_CHECKING:` and rely on the module's existing `from __future__ import annotations` | Import collaborator types at module top level | `export_dependencies.py` deliberately avoids importing the compatibility facade at module scope (its deferred imports live inside `default_export_dependencies()`). String annotations plus `TYPE_CHECKING` imports give pyright the precise types while keeping the module runtime import-cycle-free. |

## Collaborator Contracts (READ-006)

Seven fields today, six after `READ-005`. Contracts derived from actual call
sites, not the widest possible signature.

| Field | Contract | Shape source |
|---|---|---|
| `evaluate_export_gate` | `Callable[[ExportGateRequest], ExportGateDecision]` | `export_readiness.py:32`; single positional |
| `preview_playlist_file_export` | `Protocol.__call__(self, *, software: str, recommendation: PlaylistRecommendation, safe_folder: Path, requested_name: str \| None, variant_name: str \| None, generated_at: datetime \| None = ...) -> PlaylistFileExportPlan` | `playlist_file_export.py:41`; keyword-only |
| `export_playlist_file` | `Protocol.__call__(self, *, software: str, recommendation: PlaylistRecommendation, safe_folder: Path, requested_name: str \| None, variant_name: str \| None, generated_at: datetime \| None = ..., writers: PlaylistFileExportWriters \| None = ...) -> PlaylistFileExportResult` | `playlist_file_export.py:61`; keyword-only |
| `export_serato_playlist` | `Protocol.__call__(self, *, recommendation: PlaylistRecommendation, copilot_variant_name: str \| None, serato_folder: Path \| None = ..., crate_name: str \| None = ..., generated_at: datetime \| None = ..., discover_libraries: LibraryDiscoverer = ...) -> SeratoPlaylistExportResult` | `serato_playlist_export.py:85`; keyword-only. Note call site (`serato_recommendation_export.py:162`) omits `writer`, so the field contract need not expose it |
| `discover_serato_libraries` | Reuse `LibraryDiscoverer = Callable[[], list[SeratoLibrary]]` | `serato_playlist_exporter.py:40`; all params keyword-with-default, so assignable to the zero-arg alias and callable as `discover_libraries()` |
| `write_readiness_sidecars` | `Protocol.__call__(self, report: DjReadinessReport, crate_path: Path, *, safe_folder: Path \| None = ...) -> tuple[Path, Path]` | `serato_recommendation_export.py:80`; positional report/crate_path, keyword safe_folder (call site `:200`). `write_report` is bound by the compat wrapper and is not part of the bundle contract |
| ~~`write_application_dj_readiness_report`~~ | **removed** (`READ-005`) | no bundle reader |

Assignability note: the bundle is populated in `_export_dependencies()` with the
`export_coordinator.py` compatibility wrappers (`write_readiness_sidecars`,
`plan_serato_export`) whose bodies are `(*args, **kwargs)`. A variadic callable
is assignable to any `Protocol.__call__` signature under pyright, so these
wrappers satisfy the precise contracts without change.

## Flow

```text
export gate (allowed) -> export_serato_playlist -> crate ON DISK (committed)
                                                        |
                                        readiness sidecar step (try)
                                          |                     |
                                       success              ANY Exception  (was: only OSError)
                                          |                     |
                              readiness_paths set        LOGGER.exception; readiness_note set;
                                          |               readiness_paths stays (None, None)
                                          +---------+---------+
                                                    v
                          guidance label + status text (crate path always shown)
                          _record_serato_export(crate, readiness_json=None on failure)
                          on_export_success() fired ONLY when sidecar fully succeeded
```

`KeyboardInterrupt` / `SystemExit` bypass the `except Exception` clause and
propagate, so an interrupt never masquerades as partial success. No audio data
is mutated; the crate writer is never re-entered by the sidecar path.

## File Changes

| File | Change |
|---|---|
| `src/xfinaudio/desktop/serato_recommendation_export.py` | `except OSError` → `except Exception` at line 203 (RES-002). No other production edit; the crate-write block and shared post-sidecar block are untouched |
| `src/xfinaudio/desktop/export_dependencies.py` | Remove `write_application_dj_readiness_report` field (`:17`), its deferred import (`:27`) and assignment (`:40`) (READ-005). Replace the six remaining `Callable[..., Any]` fields with the contracts above; add `TYPE_CHECKING` imports and `Protocol`/alias definitions (READ-006) |
| `src/xfinaudio/desktop/export_coordinator.py` | Remove `write_application_dj_readiness_report=...` from the `_export_dependencies()` bundle constructor (`:139`). Keep the import (`:15`), `__all__` entry (`:56`), and compat-wrapper default (`:73`) |
| `tests/` (Serato export coverage) | RED test: non-`OSError` raised from `write_readiness_sidecars` after a successful crate write asserts the five outcomes (crate reported, failure surfaced in label + status, receipt recorded with `readiness_json_path=None`, callback suppressed, crate untouched by any retry) plus `LOGGER.exception` emitted. Callback-policy assertion kept explicit |

No changes to `export_actions.py`, `application/dj_readiness.py`, sidecar file
format, readiness-report content, or export-history schema.

## Interfaces / Contracts

- `ExportDependencies` shrinks by one field; all remaining fields gain precise
  static types. No positional/keyword calling convention changes at any call
  site, so behavior is unchanged.
- `ExportCoordinator.__init__`, `_export_dependencies()`, and the mixin export
  flow keep their signatures. The compatibility entrypoints stay `(*args, **kwargs)`.
- No persisted-data migration, no new runtime dependency, no `AppState` shape
  change (partial success flows through existing status/receipt paths, and any
  state update continues via `model_copy(update=...)`).

## Testing Strategy

| Layer | Coverage |
|---|---|
| Unit (RED-first) | Non-`OSError` sidecar failure → the five required outcomes + logging; explicit callback-suppression assertion; sidecar-retry-does-not-rewrite-crate assertion |
| Regression | Existing `OSError` partial-success test stays green (convergence proof); full-success path still fires the callback and records both readiness paths |
| Static | `pyright src tests` proves the new `Protocol`/alias contracts against real call sites and that the removed field breaks no consumer |
| Suite / gate | `uv run pytest -q`, `ruff check .`, `ruff format --check`, `pytest --cov --cov-fail-under=70`, `python scripts/release_gate_check.py --run` |

Strict TDD per slice: focused RED, minimal GREEN, REFACTOR, then the ordered
verification commands.

## Delivery / Review Budget

Estimated well under 400 changed lines (one `except` keyword, three field/line
removals, six contract definitions, one RED test). Deliver as a single slice.
If measurement exceeds budget, auto-chain feature-branch: `RES-002` + its test
first, then the `READ-005`/`READ-006` readability slice. Each slice reverts
independently; reverting restores the prior failure boundary and bundle shape
without touching crates, sidecars, or export history.

## Threat Matrix

| Boundary | Applicability |
|---|---|
| Audio file mutation | N/A — no audio path touched |
| Serato V2 database writes | N/A — crate-write path unchanged, no V2 writes added |
| Broadened `except` masking a real defect | Mitigated — `LOGGER.exception` preserves full traceback; only the sidecar step degrades, never the crate write; test asserts the log is emitted |
| Interrupt suppression | Mitigated by design — `except Exception` excludes `BaseException` (KeyboardInterrupt/SystemExit) |

## Open Questions

None. The callback policy (suppress on partial success) is settled above; all
`READ-005`/`READ-006` scopes are verified against call sites.
