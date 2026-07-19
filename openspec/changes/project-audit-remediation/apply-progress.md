# Apply Progress: Project Audit Remediation

Status: Corrective apply complete — 14 of 14 work units implemented; final native re-review is pending.

## Final Native Corrections — Work Unit 14.1

| Finding | Evidence |
|---|---|
| RES-001 | RED showed injected replacement discovery was ignored by metadata export. Both metadata-status and missing-field paths now resolve `discover_serato_libraries` from the same owner bundle as other export paths. |
| READ-004 | Added canonical `export_dependencies.py` with the explicit frozen bundle, owner protocol, standalone default factory, and one resolver. Removed both opaque dynamically manufactured fallback classes. |
| GREEN | Export/extraction focused suite: **28 passed**; the replacement discovery callable is forwarded by identity. |
| VERIFY | Full suite **1006 passed**; Pyright 0 errors; coverage **90.32%**; Ruff/format and release gate pass. |
| Rollback boundary | `export_dependencies.py`, the three extracted export modules, coordinator import, focused export test, and this lifecycle evidence. |

## Native 4R Corrections — Work Unit 13.1

| Finding | RED / correction evidence |
|---|---|
| READ-001 | Removed extracted-module back-imports to `export_coordinator`; `ExportDependencies` is owned/injected by `ExportCoordinator` and resolves facade globals at call time, preserving explicit injection and monkeypatch seams. |
| READ-002 / REL-001 | Removed both no-op callable wrappers; `ExportActions` resolves coordinator methods for every call. The replacement-method test proves call-time delegation. |
| READ-003 | Removed the redundant event-path `Qt` import; the module-level import remains. |
| REL-002 | Package smoke installs the translator before its safe early return while still avoiding native NSApplication configuration, MainWindow construction, and the event loop. |
| REL-003 | `sort_rows_for_column` sorts present rows directionally and appends missing numeric rows. Pure and Qt tests cover ascending and descending BPM order. |

Focused verification: **61 passed**. Full verification: **1005 passed**, Pyright 0 errors, coverage **90.23%**, Ruff/format PASS, release gate PASS.

Rollback boundary: export dependency/facade modules and tests; `app.py`/packaging smoke test; library presenter/rendering and sorting tests.

## Independent Review R3 Cleanup — Work Unit 12.1

| Evidence | Result |
|---|---|
| Change | Removed the duplicate sidebar-width block, unused `_RECOMMENDATION_READY_GUIDANCE`, unused `QCoreApplication` import, and stray standalone string from `main_window_layout.py`. |
| Behavior | No runtime contract changed; the single retained constants still drive `responsive_sidebar_width` and layout construction. |
| Focused verification | Responsive/layout selection across extracted boundaries, main window, and visual integration: **10 passed, 126 deselected**. |
| Static verification | Ruff: PASS; Pyright: 0 errors. |
| Rollback boundary | `src/xfinaudio/desktop/main_window_layout.py` only. |

## Independent Review R2 Correction — Work Unit 11.1

| Evidence | Result |
|---|---|
| RED | Four semantic-policy cases failed with missing `_is_bounded_requirement`: malformed `<garbage`, arbitrary `===local`, lower-only `>=1`, and wildcard `==1.*`. |
| GREEN | `uv run pytest -q tests/test_dependency_bounds.py tests/test_extracted_desktop_boundaries.py`: **16 passed**. |
| REFACTOR | Requirements are parsed by `packaging.requirements.Requirement`; only valid ordered upper bounds or valid non-wildcard exact pins pass. `packaging>=24,<26` is now an explicit bounded dev dependency. |
| Characterization | Successful generic write asserts forwarding/status; successful Serato write asserts backup, readiness sidecars, receipt arguments, and callback; metadata-status write asserts records/status forwarding and visible completion. |
| VERIFY | Full suite **1004 passed**; Pyright 0 errors; coverage **90.11%**; Ruff lint/format and release gate pass. |
| Rollback boundary | `tests/test_dependency_bounds.py`, `tests/test_extracted_desktop_boundaries.py`, `pyproject.toml`, and `uv.lock`. |

## Independent Review Correction — Work Unit 10.1

| Evidence | Result |
|---|---|
| RED | `tests/test_dependency_bounds.py::test_pyobjc_range_supports_python_314_compatible_release` failed against `<11`; `tests/test_desktop_app.py::test_main_resolves_default_macos_configurator_at_call_time` reached the captured native configurator and aborted, proving the seam defect. |
| GREEN | `OPENSSL_CONF=/dev/null uv run pytest -q tests/test_dependency_bounds.py tests/test_desktop_app.py tests/test_extracted_desktop_boundaries.py`: **12 passed**. |
| REFACTOR | Dependency audit now flattens main, every optional, and every dependency-group list; extraction tests assert scan wiring and three user-visible export routes; dead constants were removed and module docstrings corrected. |
| VERIFY | Full ordered gates: **997 passed**; Pyright 0 errors; coverage **90.16%**; Ruff lint/format pass; release gate pass. |
| Runtime harness | Package smoke and release-readiness smoke pass inside the release gate. |
| Rollback boundary | `pyproject.toml`, `uv.lock`, `app.py`, two extraction modules, and the three focused test files. |

## Corrective Work Unit Evidence

| Unit | Focused result | Runtime result | Rollback boundary |
|---|---|---|---|
| PR1 | Package-smoke RED failed because native configurator ran; GREEN: desktop/package tests 3 passed | Full `pytest`: 992 passed without native abort | `app.py`, desktop/package tests |
| PR2 | Prior artifact audit passed | N/A: governance-only | active OpenSpec records |
| PR3 | Prior presenter characterization passed | Included in 162-test offscreen/export suite | presenter and facade import |
| PR4 | RED `uv run pytest -q tests/test_library_screen_boundaries.py`: collection failed because `library_screen_builder` was absent. GREEN focused command: 30 passed. | Full suite 993 passed; release gate passed | `library_screen_builder.py`, `_build_ui` delegate, focused boundary test |
| PR5 | Existing filter boundary tests passed | Quick-filter paths included in focused suite | filter state and screen delegates |
| PR6 | New extraction-contract test failed before real layout/service ownership existed; GREEN passed | Visual shell navigation passed | `main_window_layout.py`, layout re-exports |
| PR7 | New extraction-contract test failed before real wiring ownership existed; GREEN passed | Scan/recommend window flows passed | `window_service_wiring.py`, layout re-exports |
| PR8 | New extraction-contract test failed on missing Serato recommendation boundary; GREEN passed | Preview/export fakes and safe Serato flows passed | software/Serato mixins and facade imports |
| PR9 | New extraction-contract test failed before metadata mixin owned the worklist methods; GREEN passed | Real-audio safe-export smoke included in 162 passed | metadata mixin and facade inheritance |

## TDD Cycle Evidence

| Task | Test | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|---|
| 1.1 | package smoke/native isolation | Unit | Existing desktop tests | Fail: native configurator invoked | 3 passed | smoke + normal startup | smoke exits before native activation |
| 2.1 | artifact audit | Governance | Existing lifecycle records | Historical failure recorded | Passed previously | evidence-present + insufficient-evidence | normalized state |
| 3.1 | presenter characterization | Unit/Qt | Existing library suite | Historical missing import | Passed previously | title + missing BPM | pure presenter |
| 4.1 | library builder ownership and widget characterization | Qt integration | Existing library/visual coverage available | `ModuleNotFoundError: xfinaudio.desktop.library_screen_builder` after removing the prior superficial extraction | `uv run pytest -q tests/test_library_screen_boundaries.py tests/test_library_screen.py tests/test_visual_integration.py`: 30 passed | concrete folder button + 12-column table, plus existing empty/populated/interaction paths | moved complete widget construction to `build_library_screen_ui`; `LibraryScreen._build_ui` is a thin delegate |
| 5.1 | filter boundary | Unit/Qt | Existing suite green | Prior missing boundary import | Passed | flags + query paths | pure filter state retained |
| 6.1 | extracted ownership contract | Unit/Qt | Existing visual suite | Import/ownership failure | Passed | narrow/wide + navigation | real composition module; facade 282 lines |
| 7.1 | extracted ownership contract | Unit/integration | Existing window suite | Missing owned wiring function | Passed | scan + recommendation | real service wiring module |
| 8.1 | extracted ownership contract | Unit/integration | Existing export suite | Missing Serato mixin/module | Passed | preview + write + denied gates | software and Serato recommendation mixins; facade 157 lines |
| 9.1 | extracted ownership contract | Unit/smoke | Existing export smoke | Missing metadata mixin ownership | Passed | status + missing-field paths | metadata worklist mixin |

## Verification Run

- Focused desktop boundaries/library/visual/export/main-window/real-audio smoke: **162 passed**.
- `uv run pytest -q`: **993 passed**, 52 warnings.
- `OPENSSL_CONF=/dev/null uv run pyright src tests`: **0 errors**.
- `uv run ruff check .`: **passed**.
- `uv run ruff format --check .`: **262 files already formatted**.
- `uv run pytest --cov --cov-fail-under=70 -q`: **993 passed; 90.02% coverage**.
- `OPENSSL_CONF=/dev/null uv run python scripts/release_gate_check.py --run`: **passed every gate**.
- Line counts: `library_screen.py` 340, `layout.py` 282, `export_coordinator.py` 157, `serato_recommendation_export.py` 271; all below 400.

## Notes

- PR4 was deliberately reverted in the working tree for this remediation: the superficial builder module/import/call were removed before the new ownership test was run and observed failing. Production extraction was then reimplemented from that RED.
- Public facade imports and monkeypatch seams remain compatible while responsibilities now live in cohesive modules.
- No audio mutation, DSP expansion, or live Serato V2 write path was added.
