# Tasks: Serato Export Partial-Success Semantics

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | ~180–260 (1 `except` clause; 3 tests/assertions added or strengthened in `tests/test_export_coordinator.py`; 3 lines removed across `export_dependencies.py` + `export_coordinator.py:139`; ~6 typed contracts / `TYPE_CHECKING` imports added in `export_dependencies.py`) |
| 400-line budget risk | Low |
| Chained PRs recommended | No — deliver as a single slice per design's default plan |
| Delivery strategy | ask-on-risk |
| Fallback chain strategy (only if measured diff exceeds 400 lines) | feature-branch-chain: RES-002 + its tests first, then the READ-005/READ-006 readability slice |

Decision needed before apply: No — proceed as a single slice; re-forecast only if the measured diff exceeds the 400-line budget, then split at the RES-002 / READ-005+READ-006 boundary as designed.

## Suggested Work Units

| Unit | Goal | Focused test | Runtime evidence | Rollback boundary |
|---|---|---|---|---|
| U1 RES-002 | Widen the sidecar-failure boundary to `except Exception` and prove the five partial-success outcomes plus explicit callback-suppression coverage for both `OSError` and non-`OSError` failures | `uv run pytest -q tests/test_export_coordinator.py -k serato_export` | Existing `OSError` partial-success path stays green; new non-`OSError` path converges identically | `src/xfinaudio/desktop/serato_recommendation_export.py:203`; `tests/test_export_coordinator.py` |
| U2 READ-005 | Remove the unused `write_application_dj_readiness_report` field from `ExportDependencies` and its bundle-construction sites, leaving the direct import in `export_actions.py` untouched | `uv run pytest -q tests/test_export_coordinator.py tests/test_export_dependencies.py` (or nearest existing dependency-bundle test module) | Full Serato/export suite still green; `export_actions.py:55` direct import unaffected | `src/xfinaudio/desktop/export_dependencies.py`; `src/xfinaudio/desktop/export_coordinator.py:139` |
| U3 READ-006 | Replace the six remaining `Callable[..., Any]` fields with precise `Protocol`/typed-alias contracts derived from real call sites, reusing `LibraryDiscoverer` | `uv run pyright src tests` plus `uv run pytest -q tests/test_export_coordinator.py` | No runtime dispatch change; pyright reports no new errors | `src/xfinaudio/desktop/export_dependencies.py` |

U2 must land after U1 (both touch the Serato export path and its tests) and before U3 (U3's contract count assumes the U2 field is already removed). All three are intended as one committed slice unless measurement forces the fallback chain.

## Work Units — Strict TDD

- [x] **1.1 RES-002 boundary widening**
  - RED: In `tests/test_export_coordinator.py`, strengthen the existing OSError partial-success test (`test_serato_export_reports_sidecar_write_failure_without_bubbling`) to pass an `on_export_success` mock and assert it is **not** called (Requirement: Success-Callback Policy). Add a new test that patches `write_readiness_sidecars` with `side_effect=ValueError(...)` (a non-`OSError`) after a successful crate write and asserts all five required outcomes: (a) `export_guidance_label` text includes the written crate path, (b) `export_guidance_label` and `status_label` text both include a sidecar-failure indication, (c) `host.serato_export_history` records the receipt with `readiness_json_path=None` / `readiness_csv_path=None`, (d) the `on_export_success` mock is **not** invoked, (e) a caplog/mock assertion confirms `LOGGER.exception` fired. Run the two tests and confirm they fail/error today (the `ValueError` currently propagates out of `export_recommendation_to_serato` uncaught).
  - GREEN: In `src/xfinaudio/desktop/serato_recommendation_export.py`, widen `except OSError as exc:` to `except Exception as exc:` at line 203. Make no other production edit — the crate-write block (lines 161–181) and the shared post-sidecar convergence block (guidance label, status text, `_record_serato_export`, callback suppression) stay untouched.
  - REFACTOR: Confirm no duplicated branch or handler was introduced; the widened clause is the entire diff. Tidy test naming/fixtures for the two strengthened/added tests if duplication appears between the `OSError` and non-`OSError` cases (e.g. shared helper for host/coordinator setup), without changing assertions.
  - VERIFY: `uv run pytest -q tests/test_export_coordinator.py -k serato_export` (focused), confirming both the pre-existing `OSError` test and the new non-`OSError` test pass, `KeyboardInterrupt`/`SystemExit` are not affected (no test needed — structural: `except Exception` cannot catch `BaseException` subclasses), then the full suite tail (section below).

- [x] **1.2 RES-002 sidecar-retry safety**
  - RED: Add a test asserting that retrying `write_readiness_sidecars` after a partial-success outcome (same crate path) does not call the crate-writing routine again and does not change the crate file's mtime/content — patch/spy on `export_serato_playlist` (or the crate writer it wraps) to assert zero additional invocations across the initial export call plus a manual retry of `write_readiness_sidecars` using the same `result.written_path`.
  - GREEN: No production change expected — the crate writer is not reachable from the sidecar boundary today; this task should require zero or near-zero production edits, confirming the design's safety claim rather than adding new code. If the assertion fails, investigate before touching the crate-write path (would indicate a defect outside this change's approved scope; escalate rather than expand scope).
  - REFACTOR: N/A (verification-only task).
  - VERIFY: `uv run pytest -q tests/test_export_coordinator.py -k retry` (or the specific test name chosen), then the full suite tail.

- [x] **2.1 READ-005 unused bundle field removal**
  - RED: Add/adjust a test that inspects `ExportDependencies` (via `dataclasses.fields`) and asserts no field named `write_application_dj_readiness_report` exists; confirm it fails against current code (the field exists today).
  - GREEN: Remove the `write_application_dj_readiness_report` field from the `ExportDependencies` dataclass (`export_dependencies.py`), remove its deferred import and assignment from `default_export_dependencies()`, and remove the `write_application_dj_readiness_report=...` keyword argument from the bundle constructor in `ExportCoordinator._export_dependencies()` (`export_coordinator.py:139`). Do not touch the module-level import (`export_coordinator.py:15`), the `__all__` re-export (`:56`), or the `write_readiness_sidecars` compatibility wrapper's `write_report` default (`:73`) — all three stay as direct-use paths independent of the bundle.
  - REFACTOR: Confirm `export_actions.py:55`'s direct import of `write_application_dj_readiness_report` still resolves and is unaffected; remove now-dead references, if any, in call sites that previously read `dependencies.write_application_dj_readiness_report` (verified none exist per design).
  - VERIFY: `uv run pytest -q tests/test_export_coordinator.py`, `uv run pyright src tests` (confirms the removed field breaks no consumer), then the full suite tail.

- [x] **3.1 READ-006 typed collaborator contracts**
  - RED: Add/adjust a test that inspects the six remaining `ExportDependencies` field type annotations (via `typing.get_type_hints` or equivalent) and asserts none resolve to `Callable[..., Any]`; confirm it fails against current code.
  - GREEN: In `export_dependencies.py`, add `if TYPE_CHECKING:` imports for the collaborator/result types needed (reusing `from __future__ import annotations` already in the module) and define: a `Callable[[ExportGateRequest], ExportGateDecision]` alias for `evaluate_export_gate`; `Protocol.__call__` classes with the exact keyword-only signatures for `preview_playlist_file_export`, `export_playlist_file`, `export_serato_playlist`, and `write_readiness_sidecars` (per the Collaborator Contracts table in `design.md`); and reuse the existing `LibraryDiscoverer = Callable[[], list[SeratoLibrary]]` alias for `discover_serato_libraries`. Apply each type to its dataclass field.
  - REFACTOR: Confirm each `Protocol` class name and contract reads cleanly (house pattern set by `PlaylistFileWriter`/`SeratoCrateWriter`/`LibraryDiscoverer`); remove any now-unused `Callable`/`Any` imports left over from the prior typing.
  - VERIFY: `uv run pyright src tests` (must report zero new errors — this is the binding acceptance check per spec), `uv run pytest -q` (full Serato/export suite unchanged), then the full suite tail.

## Full Verification Tail (run after each unit's focused check, and once more before declaring the change complete)

```bash
uv run pytest -q
uv run pyright src tests
uv run pytest --cov --cov-fail-under=70 -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/release_gate_check.py --run
```

Split any slice forecast or measured above 400 changed lines at the U1 / U2+U3 boundary described above.
