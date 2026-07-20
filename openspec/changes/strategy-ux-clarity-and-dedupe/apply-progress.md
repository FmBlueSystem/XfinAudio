# Apply Progress: Strategy UX Clarity and Duplicate Dedupe

## Status: Slice A COMPLETE — Slice B PENDING

This working tree delivers **Slice A only** (UI: description refresh +
display-name combo, Items 1+2 of `design.md`). **Slice B (pool dedupe, Item 3)
is not started** and must be applied separately per the chained-PR delivery
strategy (`state.yaml`: `chain_strategy: feature-branch-chain`). Do not
interpret this file as covering Slice B — its files
(`library/duplicate_grouping.py`, `desktop/library_filter.py`,
`recommendation/candidate_pool.py`, `application/recommendation_candidates.py`)
were not touched in this batch.

## Slice A — completed tasks (A1-A16)

All Slice A tasks in `tasks.md` are marked `[x]`. Summary per task:

- **A1** (characterization): Ran `tests/test_build_screen.py` against
  unmodified code to confirm baseline green before any edit (verified inline;
  no permanent baseline test file was kept, since A2 supersedes its intent per
  the task's own instruction to avoid a stale item-text assertion).
- **A2/A3** (RED/GREEN): Added
  `test_strategy_combo_shows_display_names_and_stores_internal_name_as_data`
  in `tests/test_build_screen.py`; confirmed RED against unmodified
  `build_screen.py` (stashed the prod file, ran pytest, saw the new test fail
  with `itemData(i) is None`/text-mismatch assertions), then implemented
  `build_screen.py:307` (`addItem(option.display_name, option.name)`) for
  GREEN.
- **A4/A5**: Added `test_on_recommend_emits_internal_strategy_name_via_current_data`;
  confirmed RED, then changed `_on_recommend` to read `strategy_combo.currentData()`.
- **A6/A7**: Added `test_recommend_reads_strategy_via_current_data` in
  `tests/test_recommendation_service_state.py` (new `_StrategyCombo` test
  double + `build_screen` override param added to `_wire_service`); confirmed
  RED against unmodified `recommendation_service.py` (stashed that one file,
  reran, saw the captured strategy equal the display label instead of the
  internal name), then changed `recommendation_service.py:145`
  (`recommend()`) to read `currentData()`.
- **A8/A9**: Added `test_on_recommend_requested_selects_item_via_find_data`;
  confirmed RED (empty `find_data_calls`), then changed
  `recommendation_service.py:224` (`on_recommend_requested`) to call
  `findData(strategy_name)` instead of `findText`.
- **A10/A11/A12**: Added
  `test_strategy_explanation_label_refreshes_immediately_on_selection_change`;
  confirmed RED against unmodified code (label stayed on the pre-switch
  description after `setCurrentIndex` with no `render()` call). Implemented:
  `BuildScreen._last_vm` storage (set at the top of `render()`), a new
  `_on_strategy_changed` slot connected to `strategy_combo.currentIndexChanged`
  in `_connect_signals`, and a `_refresh_strategy_explanation(vm)` helper
  factored out of `render()`'s old inline `current_strategy = ...` /
  `setText(...)` pair — both `render()` and `_on_strategy_changed` now call
  the same helper (REFACTOR), eliminating the duplication `design.md` called
  out.
- **A13/A14**: Added
  `test_selecting_strategy_by_display_name_resolves_to_internal_strategy_name`
  in `tests/test_build_screen.py`. Confirmed RED against unmodified code
  (`findText("Same Color & Energy")` returned `-1` since item text was still
  the internal name). No production change was needed beyond A3/A5/A7/A9 —
  the test asserts the combo resolves the display-label selection to
  `currentData() == "same_color_energy"` and that
  `default_strategy_registry().get(internal_name).name` is the same internal
  name, matching design.md's consumer audit (persistence always flows through
  `PlaylistStrategy.name`, untouched by combo text).
- **A15**: No gap found. `tests/test_playlist_strategies.py`
  (`test_strategy_descriptions_state_guarantees`, etc.) and
  `tests/test_playlist_service.py` already assert byte-identical strategy
  descriptions and unchanged `same_color`/`same_energy`/`same_color_energy`
  filtering output. Slice A does not touch `strategies.py` or
  `playlist_service.py`, so no new characterization test was added — existing
  coverage already satisfies this requirement.
- **A16**: Full verification gate run (see below). Confirmed no other raw
  `strategy_combo.currentText()` reader remains in `build_screen.py` /
  `recommendation_service.py` except the pre-existing defensive fallback at
  `build_screen.py:362` (`_refresh_strategy_explanation`:
  `currentData() or currentText()`), which `design.md` explicitly says needs
  no change.

## Additional test updates required by the display-name combo change

`design.md`/`tasks.md` flagged that any test asserting combo texts must be
updated. Found and fixed via `rg`/`grep` audit of every `strategy_combo`
reference under `tests/`:

- `tests/test_main_window.py` — 8 call sites used
  `strategy_combo.setCurrentText("warmup")` /
  `strategy_combo.setCurrentText("harmonic_journey")` (internal names, which
  were the item text pre-change). Updated to the corresponding display labels:
  `"Warmup"` (5 sites) and `"Harmonic Journey"` (4 sites, includes the one at
  line 421 counted once). All 113 tests in this file still pass after the
  update; `status_label` assertions like `"Recommended 1 track(s) using
  warmup"` needed **no change** because `RecommendationService.on_completed`
  reads `result.recommendation.strategy.name` (always internal), unaffected
  by combo text.
- `tests/test_prep_copilot_controller.py` — `_Combo("build", "Build")` test
  double already modeled `data != text` with `text` as the display label; no
  change needed (it already exercises `prep_copilot.py`'s pre-existing
  `currentData() or currentText()` defensive read).
- `tests/integration_flow.py` — standalone dev script (not `test_*.py`, not
  collected by pytest, and imports from a stale hardcoded path unrelated to
  this repo checkout). Left untouched; out of scope and not part of the
  automated test suite.

## Preserve-set / Slice B decisions

Not applicable to this batch — Slice B (which owns the
`preserved_control_paths` promote-vs-inline decision for task B9) has not
been started.

## Actual changed-line counts vs. forecast

`tasks.md`'s Slice A forecast: **~90-140 lines** (additions + deletions).

Actual (`git diff --stat`):

| File | Insertions | Deletions |
|---|---|---|
| `src/xfinaudio/desktop/recommendation_service.py` | 2 | 2 |
| `src/xfinaudio/desktop/screens/build_screen.py` | 15 | 4 |
| `tests/test_build_screen.py` | 87 | 0 |
| `tests/test_recommendation_service_state.py` | 97 | 6 |
| `tests/test_main_window.py` | 8 | 8 |
| **Total** | **209** | **20** |

**229 changed lines total** — above the 90-140 forecast (driven mainly by the
`_StrategyCombo` test double + expanded `_wire_service` in
`test_recommendation_service_state.py`, and the `test_main_window.py`
combo-text updates that were not itemized in the original forecast), but
**well inside the 400-line review budget**. Risk remains **Low** as forecast.

## Verification tail (run in this working tree)

- `uv run pytest -q` — **1142 passed**.
- `uv run pyright src tests` — **0 errors, 0 warnings, 0 informations**.
- `uv run pytest --cov --cov-fail-under=70 -q` — **1142 passed**, total
  coverage **90.70%** (required 70%).
- `uv run ruff check .` — **All checks passed!**
- `uv run ruff format --check .` — **264 files already formatted**.
- `uv run python scripts/release_gate_check.py --run` — **all gates PASS**
  (coverage, lint, format, release readiness smoke, open-source publication
  docs, publication artifact hygiene, source package hygiene, PyInstaller
  check-only, root artifact hygiene).

## Next steps

- Recommended: run `sdd-verify` for Slice A to produce `verify-report.md`
  with requirement-by-requirement evidence against
  `specs/strategy-selection-ux/spec.md`.
- Slice B (pool dedupe, Item 3 / tasks B1-B15) remains **not started** and
  must be applied in a separate PR/working tree targeting this Slice A
  branch, per the Feature Branch Chain delivery strategy.
