# Tasks: Same Color & Energy Strategy

Strict TDD. Test runner: `uv run pytest -q`. Every behavior-changing task
follows RED → GREEN → REFACTOR → VERIFY. One exception, called out
explicitly: Task 1 is a **CHARACTERIZE** step (author-first regression
snapshot), not a classic RED step, because its assertions describe *current*
behavior and are expected to pass immediately — its job is to freeze a
baseline before any production code changes, per the design.md mitigation for
"Widening name dispatch alters `same_color` behavior".

Review budget: 400 changed lines (single slice, ask-on-risk delivery). See
"Review Workload Forecast" at the end.

---

## Task 1 — CHARACTERIZE: freeze byte-identical baseline for `same_color` / `same_energy` (author FIRST)

Satisfies: *Existing Strategies Are Unaffected* (spec), D6.7 (design), Risk
"Widening name dispatch alters `same_color` behavior" (proposal).

- [x] In `tests/test_playlist_service.py`, add two new tests **before** any
      production edit in this change:
  - `test_same_color_output_and_warnings_are_stable_after_seam_widening` —
    fixed pool/anchor (reuse the `spectral_track`/`track` helpers already in
    the file), call `recommend_playlist(tracks, "same_color", controls=...)`,
    assert the exact ordered `path` list AND the exact `warnings` list
    (including `"same_color filter applied: RED"` byte-for-byte).
  - `test_same_energy_output_and_warnings_are_stable_after_seam_widening` —
    fixed pool/anchor, call `recommend_playlist(tracks, "same_energy", ...)`,
    assert the exact ordered `path` list AND exact `warnings` list (including
    `"Filtered N track(s) outside same_energy energy tolerance"` byte-for-byte
    if triggered).
- [x] Run focused: `uv run pytest -q tests/test_playlist_service.py -k stable_after_seam_widening`.
  Expected: **PASS immediately** (this is the baseline capture, not a failing
  test — do not proceed if it fails; that means the "fixed pool" assumption
  itself is wrong).
- [x] Do not touch `src/xfinaudio/recommendation/playlist_service.py` or
      `strategies.py` in this task. These two tests are the regression guard
      re-run after every later task in this change.

Parallelizable: No — this is the explicit design-mandated first step; all
later production edits must be checked against it.

---

## Task 2 — RED: strategy registration & enumeration tests fail

Satisfies: *Strategy Registration and Enumeration* (spec, both scenarios).

- [x] In `tests/test_playlist_strategies.py`, add `"same_color_energy"` to the
      module-level `EXPECTED_STRATEGIES` set (line ~16–26). This alone makes
      `test_available_strategies_contains_supported_strategy_names`,
      `test_default_strategy_registry_lists_all_current_strategies`, and the
      parametrized `test_get_strategy_returns_profile_with_weights_and_hints`
      fail because the profile is not yet registered.
- [x] Add a dedicated test `test_same_color_energy_registers_with_expected_profile`
      asserting: `display_name == "Same Color & Energy"`, `energy_tolerance == 1`,
      and `weights == ScoringWeights(harmonic=0.25, bpm=0.15, energy=0.30, tags=0.10, spectral=0.20)`
      (D2 weights, verbatim).
- [x] In `tests/test_application_strategy_catalog.py`, add
      `test_list_strategy_catalog_includes_same_color_energy` asserting an
      entry with `name == "same_color_energy"` and
      `display_name == "Same Color & Energy"` is present in
      `list_strategy_catalog()`. This exercises the "no bespoke UI wiring"
      success criterion end-to-end through the application boundary used by
      `BuildViewModel.available_strategies()`.
- [x] Run focused: `uv run pytest -q tests/test_playlist_strategies.py tests/test_application_strategy_catalog.py`.
      Expected: **FAIL** (RED) — `"Unknown playlist strategy"` / set-mismatch /
      missing-catalog-entry errors.

Parallelizable: Can run as its own track alongside Task 1 (different files,
no shared state), but must complete (RED confirmed) before Task 3.

---

## Task 3 — GREEN: register `same_color_energy` in `strategies.py`

Satisfies: *Strategy Registration and Enumeration* (spec).

- [x] In `src/xfinaudio/recommendation/strategies.py`:
  - Add `"same_color_energy"` to the `StrategyName` Literal (after
    `"same_genre"`, line ~21).
  - Add a `_STRATEGIES["same_color_energy"]` entry: `name="same_color_energy"`,
    `display_name="Same Color & Energy"`, description per proposal intent,
    `weights=ScoringWeights(harmonic=0.25, bpm=0.15, energy=0.30, tags=0.10, spectral=0.20)`,
    `energy_tolerance=1`. No `energy_range`, `bpm_range`, or `sort_hint`
    override (defaults match `same_color`'s pattern).
- [x] Run focused: `uv run pytest -q tests/test_playlist_strategies.py tests/test_application_strategy_catalog.py`.
      Expected: **PASS** (GREEN) — including the catalog test, with zero
      changes to `strategy_catalog.py` or `build_view_model.py` (confirms the
      "no bespoke UI wiring" success criterion).
- [x] Re-run Task 1's two characterization tests. Expected: still **PASS**
      byte-identical (registration is additive-only; no dispatch touched yet).

Parallelizable: No — depends on Task 2 (RED confirmed first).

---

## Task 3b — RED+GREEN: guarantee-explicit descriptions

Satisfies: *Guarantee-Explicit Descriptions* (spec; user feedback 2026-07-19).

- [x] RED: in `tests/test_playlist_strategies.py`, add
      `test_strategy_descriptions_state_guarantees` asserting (substring
      checks, not full literals):
      - `same_color_energy` description mentions both the hard anchor-color
        filter and the hard "±1" energy band.
      - `same_color` description states the anchor color is a hard filter
        ("Only tracks matching..." style) and that energy is not constrained.
      - `same_energy` description states the hard "±1" band and that color
        is weighted but not limited.
      Run focused; expected **FAIL** for the two existing profiles' copy.
- [x] GREEN: update the `description` strings of `same_color` and
      `same_energy` in `_STRATEGIES` (copy-only; no other field), e.g.:
      - same_energy: "Hard limit: only tracks within ±1 energy level of the
        anchor. Color is weighted but not limited."
      - same_color: "Hard filter: only tracks matching the anchor's spectral
        color. Energy is weighted but not limited."
      - same_color_energy (set in Task 3): "Hard filters: only tracks
        matching the anchor's color AND within ±1 energy level of the
        anchor."
      Run focused; expected **PASS**. Confirm no other test asserts the old
      literals (`rg` for the previous description strings across tests/).

---

## Task 4 — REFACTOR: strategies.py

- [x] Review the new `_STRATEGIES` entry for naming/formatting consistency
      with neighboring entries (e.g. `same_color`, `same_genre`). No behavior
      change expected; if none needed, mark as no-op and proceed.
- [x] Run `uv run pytest -q tests/test_playlist_strategies.py tests/test_application_strategy_catalog.py`
      to confirm still green after any refactor.

---

## Task 5 — VERIFY: strategies.py slice

- [x] `uv run pytest -q tests/test_playlist_strategies.py tests/test_application_strategy_catalog.py`
- [x] `uv run pyright src/xfinaudio/recommendation/strategies.py tests/test_playlist_strategies.py`

---

## Task 6 — RED: widen color-filter dispatch + strategy-aware warnings (playlist_service.py)

Satisfies: *Hard Anchor-Color Prefilter Applies*, *Hard Energy Band Composes
With the Color Filter*, *Control Paths Are Preserved*, *Empty-Pool Fallback
With Strategy-Aware Warning* (spec, all scenarios).

- [x] In `tests/test_playlist_service.py`, add (all using `"same_color_energy"`
      as `strategy_name`):
  - `test_same_color_energy_filters_candidates_to_anchor_color` — mirrors
    `test_same_color_filters_candidates_to_selected_start_color`; assert every
    non-control candidate shares the anchor's dominant color.
  - `test_same_color_energy_enforces_energy_tolerance` — mirrors
    `test_same_energy_filters_candidates_outside_anchor_energy_tolerance`;
    assert every non-control candidate is within ±1 of anchor energy.
  - `test_same_color_energy_composes_color_and_energy_simultaneously` — mixed
    pool with tracks that satisfy color-only, energy-only, both, or neither;
    assert survivors satisfy color AND ±1 energy together (proves composition,
    not substitution — D6.4).
  - `test_same_color_energy_preserves_control_paths` — locked, start, end, and
    manual-prefix tracks that violate color and/or energy; assert all remain
    present in their existing positions (mirrors
    `test_same_color_preserves_controlled_paths_even_when_color_differs`).
  - `test_same_color_energy_falls_back_on_empty_color_pool_with_named_warning`
    — **build the empty-pool case via a color mismatch only** (per design D4:
    only the color filter has a fallback path; energy-empty is terminal,
    matching `same_energy`). Anchor is e.g. RED with some energy; all
    non-control candidates are e.g. GREEN/BLUE (so the color filter alone
    empties the eligible pool) but all fall within the energy band. Assert
    fallback-to-unfiltered scoring AND a warning naming `"same_color_energy"`
    (not `"same_color"`).
  - `test_prefilter_strategy_candidates_applies_color_and_energy_for_same_color_energy`
    — mirrors `test_prefilter_strategy_candidates_keeps_only_anchor_color_for_same_color`
    and `..._applies_energy_tolerance_for_same_energy`; assert the capped pool
    satisfies both hard filters.
- [x] Run focused: `uv run pytest -q tests/test_playlist_service.py -k same_color_energy`.
      Expected: **FAIL** (RED) — color assertions fail because
      `strategy.name == "same_color"` (lines 162, 392) does not yet match
      `"same_color_energy"`, so the color filter never runs and warnings never
      name the new strategy.

Parallelizable: No — depends on Task 3 (registration must exist so
`get_strategy("same_color_energy")` resolves).

---

## Task 7 — GREEN: implement the widened seam and strategy-aware warnings

Satisfies: same requirements as Task 6, plus *Existing Strategies Are
Unaffected* (via Task 1 regression guard).

In `src/xfinaudio/recommendation/playlist_service.py`:

- [x] Add a module-level constant near the top (after `MAX_ADJACENT_BPM_DIFFERENCE_PERCENT`,
      line ~27): `_COLOR_FILTER_STRATEGIES: frozenset[str] = frozenset({"same_color", "same_color_energy"})`
      (design D1, Route A — selected).
- [x] Replace `if strategy.name == "same_color":` at line 162
      (`recommend_playlist`) with `if strategy.name in _COLOR_FILTER_STRATEGIES:`.
- [x] Replace `if strategy.name == "same_color":` at line 392
      (`prefilter_strategy_candidates`) with the same membership check.
- [x] Add a `strategy_name: str` parameter to `_apply_color_filter` (line 406).
      Update both call sites (162–166 and 392–393) to pass `strategy.name`.
- [x] In `_apply_color_filter`, interpolate `strategy_name` into both warning
      lines (design D3):
  - Line 413: `f"{strategy_name} filter applied: {anchor_color}"` (was
    hardcoded `"same_color filter applied: ..."`).
  - Line 418: `f"{strategy_name}: no candidates match anchor color '{anchor_color}'; falling back to unfiltered scoring"`.
- [x] In `_apply_energy_tolerance` (line 512), interpolate `strategy.name`:
      `f"Filtered {removed} track(s) outside {strategy.name} energy tolerance"`
      (was hardcoded `"...outside same_energy energy tolerance"`).
- [x] Run focused: `uv run pytest -q tests/test_playlist_service.py -k same_color_energy`.
      Expected: **PASS** (GREEN).
- [x] Re-run Task 1's two characterization tests. Expected: **PASS**
      byte-identical — `strategy.name` interpolation for `"same_color"` and
      `"same_energy"` reproduces the exact prior literal text, so this is the
      proof the widened seam and D3 interpolation did not alter existing
      behavior.

Parallelizable: No — depends on Task 6 (RED confirmed first) and Task 1
(baseline must exist to validate against).

---

## Task 8 — REFACTOR: playlist_service.py

- [x] Review the new frozenset constant placement and parameter threading for
      consistency with the existing `_apply_genre_filter`/`_apply_strategy_filters`
      style (name-equality dispatch, warnings-list return convention). No
      behavior change expected.
- [x] Run `uv run pytest -q tests/test_playlist_service.py` to confirm still
      green after any refactor.

---

## Task 9 — VERIFY: playlist_service.py slice

- [x] `uv run pytest -q tests/test_playlist_service.py tests/test_playlist_strategies.py tests/test_application_strategy_catalog.py`
- [x] `uv run pyright src/xfinaudio/recommendation/playlist_service.py src/xfinaudio/recommendation/strategies.py tests/test_playlist_service.py`

---

## Task 10 — VERIFY: no elsewhere-hardcoded strategy-name string breaks

Satisfies: orchestrator note "verify no test elsewhere asserts hardcoded
`same_color filter applied`/`same_energy` strings the interpolation would
break."

- [x] Confirm via repo-wide search that `"same_color filter applied"`,
      `"same_color:"`, and `"outside same_energy"` are asserted **only** in
      `tests/test_playlist_service.py` (already confirmed during this tasks
      phase: no other test file references these strings). Record this as a
      pass/fail check, no new test needed if confirmed.
- [x] If any other file is found asserting these strings (e.g. new tests
      landed after this tasks doc was written), update it to expect
      `strategy.name`-interpolated text instead, and re-run its suite.

---

## Task 11 — VERIFY: UI strategy dropdown enumerates automatically

Satisfies: *Strategy Registration and Enumeration* success criterion "The
strategy appears in the UI strategy dropdown automatically."

- [x] Confirm `src/xfinaudio/desktop/build_view_model.py:available_strategies()`
      (line ~41) sources its `StrategyOption` list from
      `list_strategy_catalog()` (application boundary) with no hardcoded
      strategy-name list. Already confirmed during this tasks phase — no
      production edit needed in `build_view_model.py`.
- [x] Task 2/3's `test_list_strategy_catalog_includes_same_color_energy` is the
      executable proof of this; no additional desktop-layer test required
      given `BuildViewModel` has no strategy-specific branching.

---

## Task 12 — VERIFY: full type-check

- [x] `uv run pyright src tests` (full run — confirms the `StrategyName`
      Literal extension introduces no new errors anywhere, including
      `desktop/build_view_model.py` and any other `StrategyName`-typed call
      site).

---

## Task 13 — VERIFY: full release-gate suite

- [x] `uv run pytest -q`
- [x] `uv run pyright src tests`
- [x] `uv run pytest --cov --cov-fail-under=70 -q`
- [x] `uv run ruff check .`
- [x] `uv run ruff format --check .`
- [x] `uv run python scripts/release_gate_check.py --run`
- [x] Record results in `apply-progress.md` (created during apply phase) and
      carry evidence into `verify-report.md` (verify phase).

---

## Review Workload Forecast

- **Estimated changed lines**: ~260–300 total (includes Task 3b
  guarantee-explicit descriptions: ~4 copy lines + ~25 test lines).
  - `src/xfinaudio/recommendation/strategies.py`: ~9 lines (1 Literal member +
    ~8-line `_STRATEGIES` entry).
  - `src/xfinaudio/recommendation/playlist_service.py`: ~20 lines (1 frozenset
    constant, 2 widened dispatch checks, 1 new parameter + 2 call-site
    updates, 2 warning interpolations, 1 energy-tolerance interpolation).
  - `tests/test_playlist_strategies.py`: ~20 lines (1 set update + 1 new
    registration test).
  - `tests/test_application_strategy_catalog.py`: ~8 lines (1 new test).
  - `tests/test_playlist_service.py`: ~170–200 lines (2 characterization tests
    + 6 new `same_color_energy` behavior tests, each with track-pool setup).
- **Chained-PR recommendation**: **Not required.** The forecast sits well
  under the 400-line review budget as a single slice, consistent with the
  proposal's "Expected to fit the 400-line review budget as a single slice."
- **Budget risk**: **Low.** Even a generous overrun (extra edge-case tests)
  is unlikely to approach 400 lines; the production diff is small and
  concentrated in two files.
- **Decision-needed flag**: **False.** No ask-on-risk escalation required
  before apply; proceed as a single PR/review cycle. Re-evaluate only if
  apply-phase discovery reveals additional call sites keyed on
  `strategy.name == "same_color"` or `"same_energy"` beyond the two documented
  in design.md (lines 162, 392, 512).

## Parallelization Summary

- Track A (sequential, required first): Task 1 (characterization baseline).
- Track B (can start once Task 1 is filed, independent file): Task 2 → 3 → 4
  → 5 (strategies.py registration).
- Track C (depends on Track B's Task 3 landing): Task 6 → 7 → 8 → 9
  (playlist_service.py seam + warnings).
- Task 10, 11 are verification-only checks, already largely confirmed during
  this tasks-authoring pass; they gate sign-off, not further code.
- Tasks 12–13 are the final sequential full-suite gate; they cannot run until
  Tracks B and C are both green.
- Given the small total size (~250 lines), true parallel sub-agent execution
  offers little value here — a single sequential implementer following this
  order is recommended over splitting work across agents.
