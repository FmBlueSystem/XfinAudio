# Apply Progress: Project Audit Remediation

Status: Complete after corrective apply — 9 of 9 work units implemented; verification rerun is required.

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
