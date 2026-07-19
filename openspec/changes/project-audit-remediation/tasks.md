# Tasks: Project Audit Remediation

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 2,300–3,000 across chain |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Delivery strategy | auto-chain |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

## Suggested Work Units

| Unit/base | Goal | Focused test | Runtime evidence | Rollback boundary |
|---|---|---|---|---|
| PR1/tracker | Startup seam + bounded lock | `uv run pytest -q tests/test_desktop_app.py` | package smoke | `app.py`, dependencies |
| PR2/PR1 | Reconcile active SDD records | `uv run python scripts/release_gate_check.py --run` | N/A: artifact-only | active OpenSpec files |
| PR3/PR2 | Library table presenter | `uv run pytest -q tests/test_library_screen.py` | offscreen rows | presenter + adapter |
| PR4/PR3 | Library UI builder | `uv run pytest -q tests/test_library_screen.py tests/test_visual_integration.py` | offscreen UI | builder + adapter |
| PR5/PR4 | Library filter state | `uv run pytest -q tests/test_library_screen.py` | quick filters | filter + adapter |
| PR6/PR5 | Main-window layout | `uv run pytest -q tests/test_visual_integration.py` | navigation | layout + facade |
| PR7/PR6 | Service wiring | `uv run pytest -q tests/test_main_window.py` | scan/recommend | wiring + facade |
| PR8/PR7 | Software/Serato export split | `uv run pytest -q tests/test_export_coordinator.py` | preview/export fakes | two collaborators + facade |
| PR9/PR8 | Metadata/history export split | `uv run pytest -q tests/test_export_coordinator.py tests/test_smoke_real_audio_scan_recommend_export.py` | safe-export smoke | metadata collaborator + facade |

Each child targets the previous PR branch; retarget/rebase polluted child diffs.

## Work Units — Strict TDD

Corrective apply reopened PR4–PR9 after the failed verify report. PR4 was subsequently reverted in isolation and re-executed through a current, observed RED → GREEN → REFACTOR cycle; exact evidence is recorded in `apply-progress.md`.

- [x] **1.1 PR1** — RED: prove injected macOS activation avoids native singleton and audit unbounded declarations. GREEN: add adapter, compatible upper bounds, synchronized `uv.lock`. REFACTOR: narrow seam. VERIFY: focused test, `uv lock --check`, full gates.
- [x] **2.1 PR2** — RED: record failing active-change audit. GREEN: add evidence-backed artifacts/status without editing archives. REFACTOR: normalize schema. VERIFY: release gate and artifact matrix.
- [x] **3.1 PR3** — RED: characterize sorting, rows, selection, highlights. GREEN: extract `library_table_presenter.py`. REFACTOR: narrow host API. VERIFY: focused and full gates.
- [x] **4.1 PR4** — RED: characterize widgets, labels, signals, accessibility. GREEN: extract `library_screen_builder.py`. REFACTOR: private builders. VERIFY: focused and full gates.
- [x] **5.1 PR5** — RED: characterize query/quick-filter restoration and emissions. GREEN: extract `library_filter_state.py`. REFACTOR: isolate pure matching. VERIFY: focused and full gates.
- [x] **6.1 PR6** — RED: characterize sidebar/layout/visibility. GREEN: extract `main_window_layout.py` with re-exports. REFACTOR: remove duplication. VERIFY: focused and full gates.
- [x] **7.1 PR7** — RED: characterize scan/recommend wiring/restoration. GREEN: extract `window_service_wiring.py`. REFACTOR: keep thin `layout.py` delegates. VERIFY: focused and full gates.
- [x] **8.1 PR8** — RED: characterize gates, previews, writes, backups, sidecars. GREEN: extract generic and Serato recommendation collaborators. REFACTOR: preserve facade signatures. VERIFY: focused and full gates.
- [x] **9.1 PR9** — RED: characterize metadata worklists, receipts, bounded history. GREEN: extract metadata/history collaborator. REFACTOR: narrow `ExportHost`. VERIFY: focused, smoke, and full gates.
- [x] **10.1 Review corrections** — RED: reproduce the Python 3.14 dependency-range failure and default-configurator capture; replace structural-only extraction checks with behavioral characterization. GREEN: widen pyobjc to `<13`, lock 12.2.1, resolve the configurator at call time, audit all dependency groups, and remove dead extraction constants. REFACTOR: accurate module docstrings and focused fake-host tests. VERIFY: 12 focused tests plus all ordered project gates.
- [x] **11.1 R2 review corrections** — RED: reject malformed/non-ordering dependency constraints and characterize successful generic, Serato, and metadata writes. GREEN: parse requirements semantically with `packaging`, declare its bounded dev dependency, and assert forwarded write arguments plus backup/sidecar/history/callback effects. VERIFY: 16 focused tests and all ordered gates.
- [x] **12.1 R3 cleanup correction** — Remove duplicated sidebar constants, unused recommendation translation/import, and stray standalone extraction string from `main_window_layout.py` without behavior change. VERIFY: focused responsive/layout suite, Ruff, and Pyright.

Split any slice forecast or measured above 400 changed lines.
