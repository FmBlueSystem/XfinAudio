# Tasks: Strategy UX Clarity and Duplicate Dedupe

## How to read this checklist

- Delivery is **two chained slices**, matching `design.md`'s recommended split.
  **Slice A (UI, Items 1+2) ships first**; **Slice B (pool dedupe, Item 3)**
  ships second. The slices have no functional ordering dependency on each
  other (disjoint files) — the sequencing is a delivery/review-budget choice,
  not a technical requirement.
- Every behavior-changing task follows strict TDD: **RED** (write/extend a
  failing test) → **GREEN** (smallest production change) → **REFACTOR** →
  **VERIFY** (focused test, then full suite).
- Characterization tasks are called out explicitly where `design.md` requires
  a byte-identical regression guard.
- Each task lists its spec requirement(s) so verify can trace back.

---

## Slice A — UI: description refresh + display-name combo

Files: `src/xfinaudio/desktop/screens/build_screen.py`,
`src/xfinaudio/desktop/recommendation_service.py`, `tests/test_build_screen.py`,
`tests/test_recommendation_service_state.py`.

Spec: `specs/strategy-selection-ux/spec.md` — all requirements.

### A1. Characterization — lock current combo/label behavior before touching it [x]

- **RED/characterization**: Add a test asserting today's baseline still holds
  pre-change: combo items are internal names (`self.strategy_combo.itemText(i)
  == option.name`), and `render()` sets `strategy_explanation_label` from
  `currentData() or currentText()`. This is a safety net, not a new
  requirement — it documents current behavior so later edits can prove intent
  (item text becomes display name; item data becomes internal name).
- **VERIFY**: `uv run pytest -q tests/test_build_screen.py` passes against
  unmodified code.
- Requirement: baseline guard for both `strategy-selection-ux` requirements
  below.

### A2. RED — display-name combo items, internal name as item data [x]

- Add a failing test: after `render()`, every combo item's visible text
  (`itemText(i)`) equals `option.display_name`, no item's visible text equals
  any internal strategy name, and `itemData(i)` equals `option.name` for every
  index.
- Requirement: Spec `strategy-selection-ux` → "Selector Shows Display Names" /
  "Combo items show display names".

### A3. GREEN — `build_screen.py:307` combo population [x]

- Change `self.strategy_combo.addItem(option.name)` to
  `self.strategy_combo.addItem(option.display_name, option.name)`.
- **VERIFY**: A2 test passes; A1 characterization test is updated (not
  invented-new) to reflect the new intentional item-text change, or superseded
  by A2 — do not leave a stale baseline assertion that visible text is the
  internal name.

### A4. RED — `_on_recommend` emits the internal name via `currentData()` [x]

- Add a failing test asserting `_on_recommend` emits
  `self.strategy_combo.currentData()` (the internal name), not
  `currentText()` (now the display label), on `recommend_requested`.
- Requirement: Spec `strategy-selection-ux` → "Selecting a display name
  resolves the internal strategy".

### A5. GREEN — `build_screen.py:404-406` (`_on_recommend`) [x]

- Change `strategy = self.strategy_combo.currentText()` to
  `strategy = self.strategy_combo.currentData()`.
- **VERIFY**: A4 passes.

### A6. RED — `RecommendationService.recommend` reads `currentData()` [x]

- Add a failing test in `tests/test_recommendation_service_state.py` (or the
  covering suite) asserting `recommend()` reads the strategy name via
  `strategy_combo.currentData()`, not `currentText()`.
- Requirement: Spec `strategy-selection-ux` → "Downstream Consumers Keep
  Working" / "Recommendation and prep copilot resolve the selection".

### A7. GREEN — `recommendation_service.py:145` (`recommend`) [x]

- Change the `currentText()` read to `currentData()`.
- **VERIFY**: A6 passes.

### A8. RED — `on_recommend_requested` selects the item via `findData` [x]

- Add a failing test asserting `on_recommend_requested(strategy_name, paths)`
  locates the combo index via `strategy_combo.findData(strategy_name)` (an
  internal name), not `findText(strategy_name)` (which would fail once combo
  text is the display label).
- Requirement: Spec `strategy-selection-ux` → "Downstream Consumers Keep
  Working".

### A9. GREEN — `recommendation_service.py:224` (`on_recommend_requested`) [x]

- Change `combo_idx = self._build_screen.strategy_combo.findText(strategy_name)`
  to `combo_idx = self._build_screen.strategy_combo.findData(strategy_name)`.
- **VERIFY**: A8 passes.

### A10. RED — immediate label refresh on selection change (no re-render) [x]

- Add a failing Qt-offscreen test: after `render()`, call
  `strategy_combo.setCurrentIndex(...)` to switch strategies (e.g.
  `same_color` → `same_color_energy`) **without calling `render()` again**,
  and assert `strategy_explanation_label.text()` immediately equals the newly
  selected strategy's description.
- Requirement: Spec `strategy-selection-ux` → "Immediate Description Refresh
  on Selection" (both scenarios).

### A11. GREEN — wire `currentIndexChanged` to a new internal slot [x]

- Add `BuildScreen._on_strategy_changed`, connected in `_connect_signals` to
  `strategy_combo.currentIndexChanged`. Store the last-rendered ViewModel
  (e.g. `self._last_vm`, mirroring the `LibraryScreenRenderingMixin` pattern)
  in `render()`. The slot sets `strategy_explanation_label` from
  `self._last_vm.strategy_explanation(self.strategy_combo.currentData())`,
  guarded by `if self._last_vm is not None`.
- **VERIFY**: A10 passes.

### A12. REFACTOR — remove duplication between `render()` and the new slot [x]

- Both `render()` (line ~338-339) and `_on_strategy_changed` derive the label
  from the same `(currentData(), vm)` pair. Factor the shared line into one
  private helper (e.g. `_refresh_strategy_explanation(vm)`) called from both
  places, to avoid future drift between the two call sites design.md calls
  out as "byte-identical because both derive from the identical source".
- **VERIFY**: A2, A10, A11 tests plus the rest of `test_build_screen.py`
  stay green.

### A13. RED — export JSON keeps the internal strategy name [x]

- Add/extend a test: generate a recommendation after selecting a strategy by
  its display name (through the combo path), export to JSON, and assert
  `recommendation.strategy.name` equals the internal name (e.g.
  `same_color_energy`), never the display label.
- Requirement: Spec `strategy-selection-ux` → "Persisted and Exported
  Artifacts Record Internal Names".

### A14. VERIFY — A13 passes with no production change expected [x]

- This should already pass once A3/A5/A7/A9 land, because
  `PlaylistStrategy.name` (internal) is what flows into
  `recommendation.strategy.name` regardless of combo text — per design.md's
  consumer audit. If it fails, that signals a missed raw-`currentText()` site;
  re-audit `prep_copilot.py:65` and any other combo reader before touching
  `playlist_exporters.py`.
- Requirement: same as A13.

### A15. Characterization — filtering/description output unchanged [x]

- Add/confirm a test that strategy `description` text is byte-identical
  before/after this slice, and that a fixed pool + anchor produces an
  identical ordered candidate list and warnings under `same_color`,
  `same_energy`, `same_color_energy` (existing `tests/test_playlist_service.py`
  / `tests/test_playlist_strategies.py` coverage should already assert this —
  extend only if a gap exists; do not weaken existing assertions).
- Requirement: Spec `strategy-selection-ux` → "Filtering Semantics and
  Descriptions Are Unaffected" (both scenarios).

### A16. VERIFY — Slice A full gate [x]

- Run `uv run pytest -q`, `uv run pyright src tests`,
  `uv run pytest --cov --cov-fail-under=70 -q`, `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run python scripts/release_gate_check.py --run`.
- Confirm no other raw `strategy_combo.currentText()` reader remains (grep
  `currentText()` in `build_screen.py` and `recommendation_service.py`).

**Slice A parallelism**: A1–A9 are sequential (each GREEN depends on its own
RED, and A3/A5/A7/A9 touch overlapping combo semantics that must land in
order: item data must exist — A3 — before A5/A7/A9 read `currentData()`
meaningfully). A10–A12 (label refresh) can be developed in parallel with
A2–A9 (display-name plumbing) since they touch different lines of the same
file but different behaviors — but land them in the same PR to avoid a
half-migrated combo state. A13–A15 are verification/characterization tasks
that depend on A3–A9 being GREEN. Recommended solo-implementer order: A1 → A2
→ A3 → A4 → A5 → A6 → A7 → A8 → A9 → A10 → A11 → A12 → A13 → A14 → A15 → A16.

### Slice A — Review Workload Forecast

- **Estimated changed lines**: ~90-140 (additions + deletions), across
  `build_screen.py` (~25-40 lines: new slot, `_last_vm` storage, `addItem`
  change, `_on_recommend` change, refactor helper), `recommendation_service.py`
  (~4-8 lines: two one-line reads), and tests (~60-90 lines: new/extended RED
  tests across `test_build_screen.py` and
  `test_recommendation_service_state.py`).
- **Chained-PR recommendation**: Ship as **PR1**, targeting the feature
  branch (first in the chain). Self-contained; independently revertible.
- **400-line budget risk: Low**
- **Decision needed before apply: No**
- **Chained PRs recommended: Yes** (this is PR1 of the 2-slice chain; PR2 is
  Slice B below — the chain is what already keeps each slice inside budget)

---

## Slice B — Pool: relocate grouping helpers + dedupe before the 25-cap

Files: `src/xfinaudio/library/duplicate_grouping.py` (NEW),
`src/xfinaudio/desktop/library_filter.py`,
`src/xfinaudio/recommendation/candidate_pool.py`,
`src/xfinaudio/application/recommendation_candidates.py`,
`src/xfinaudio/recommendation/controls.py` (optional promotion),
`tests/test_library_filter.py`, `tests/test_recommendation_presenter.py` (or a
new `tests/test_candidate_pool.py`), `tests/test_application_recommendation_candidates.py`.

Spec: `specs/recommendation-duplicate-version-dedupe/spec.md` — all
requirements.

### B1. Characterization — library display filter is byte-identical before relocation

- **RED/characterization**: Before touching `library_filter.py`, confirm
  `tests/test_library_filter.py` passes unmodified against current code (this
  is the pre-change snapshot). Record that this suite must stay green with
  **zero edits** through the rest of Slice B — the design mandates the
  Library-screen display filter is untouched.
- **VERIFY**: `uv run pytest -q tests/test_library_filter.py` — baseline
  green.
- Requirement: design.md "Regression surface & safety" — Library screen
  display filter unchanged; guards Spec's "Filtering Semantics" analog for
  the display path (not itself a numbered dedupe-spec requirement, but a
  hard non-regression gate the spec's control-immunity/no-change
  requirements depend on).

### B2. RED — new `library/duplicate_grouping.py` neutral helpers

- Add failing tests (new test module, e.g.
  `tests/test_duplicate_grouping.py`) for:
  - `normalize_title_for_grouping` / `normalize_artist_for_grouping` produce
    the same normalization as today's `_normalize_*_for_grouping` (suffix
    stripping, casefold, parens-as-punctuation).
  - `duplicate_group_key(title, artist, *, placeholder=None)` returns `None`
    for blank/placeholder title or artist when a placeholder is supplied, and
    is Qt-free / `desktop`-import-free (no dependency on `_DASH` or
    `desktop.library_view_model`).
  - `duplicate_representative_sort_key(*, is_complete, missing_field_count,
    title, path)` reproduces the exact tuple ordering used today:
    `(0 if complete else 1, missing_field_count, len(title), path)`.
- Requirement: design.md Decision 3a (layering); underpins spec's "Candidate
  Pool Keeps One Representative per Group" and "Representative Choice Is
  Deterministic".

### B3. GREEN — implement `library/duplicate_grouping.py`

- Create the module with the three/four pure functions per design.md 3a,
  parametrizing `placeholder` instead of importing `_DASH`.
- **VERIFY**: B2 passes. Confirm no import from `xfinaudio.desktop.*` exists
  in the new module (`recommendation` importing `library` must not transitively
  reach `desktop`).

### B4. RED — `library_filter.py` delegates without behavior change

- Extend/add a test asserting `desktop/library_filter.py`'s
  `_duplicate_group_key`, `_normalize_title_for_grouping`,
  `_normalize_artist_for_grouping` now delegate to
  `library.duplicate_grouping` (e.g. via a thin wrapper that calls the new
  functions with `placeholder=_DASH`), while producing identical output to
  the B1 characterization baseline for the same fixtures.
- Requirement: design.md 3a "imports only, no logic change".

### B5. GREEN — relocate delegation in `library_filter.py`

- Replace the local normalization/group-key bodies with thin calls into
  `library.duplicate_grouping` (`placeholder=_DASH` for the group-key call);
  keep `_RowInfo`, `_pick_duplicate_representative`, `suppressed_duplicate_paths`
  as-is except `_pick_duplicate_representative`'s sort key now calls
  `duplicate_representative_sort_key` from the neutral module.
- **VERIFY**: `uv run pytest -q tests/test_library_filter.py` — **must stay
  green with the ORIGINAL test file unmodified** (per design.md and B1). Also
  run B2/B4.

### B6. RED — `dedupe_recommendation_duplicates` collapses a duplicate group

- Add a failing test (`tests/test_candidate_pool.py`, new or extended) using
  a "Too Hot" x2 fixture (same artist, differing only by a generated suffix):
  after `dedupe_recommendation_duplicates(records, controls)`, exactly one
  representative survives, and it is the complete / fewer-missing /
  shorter-title / path-tiebreak choice per
  `duplicate_representative_sort_key`.
- Requirement: Spec `recommendation-duplicate-version-dedupe` → "Candidate
  Pool Keeps One Representative per Group" (both scenarios).

### B7. RED — control-path immunity

- Add failing tests:
  - A duplicate group containing a locked track: the locked track survives,
    non-control duplicate(s) in the same group are removed.
  - A duplicate group containing the anchor/start, end, or a manual-order
    track: that control track survives regardless of position in the group.
- Requirement: Spec `recommendation-duplicate-version-dedupe` → "Control
  Tracks Are Never Removed by Dedupe" (both scenarios).

### B8. RED — determinism and no-duplicates characterization

- Add failing tests:
  - Deduping the same fixed duplicate group twice in separate runs picks the
    same representative both times.
  - A pool where every title+artist key is unique is byte-identical
    before/after `dedupe_recommendation_duplicates` (order-preserving,
    nothing suppressed).
- Requirement: Spec `recommendation-duplicate-version-dedupe` →
  "Representative Choice Is Deterministic"; "Duplicate-Free Libraries Are
  Unchanged" / "No duplicates means no change".

### B9. GREEN — implement `dedupe_recommendation_duplicates` in `candidate_pool.py`

- Implement per design.md 3b: build the `preserve` set (manual ∪ start ∪ end
  ∪ locked − excluded), group by `duplicate_group_key(title, artist,
  placeholder=None)`, keep controls-in-group when present, otherwise keep the
  `min(...)` by the adapted representative sort key, suppress the rest,
  return `[r for r in records if r.path not in suppressed]` preserving
  original order.
- **Preserve-set sourcing decision** (per design.md's open decision): default
  to promoting `_preserved_control_paths` from `playlist_service.py` to a
  public `preserved_control_paths` in `recommendation/controls.py` and calling
  it from both `playlist_service.py` and `candidate_pool.py`, IF this stays
  within Slice B's line budget; otherwise inline an equivalent 4-line set
  build directly in `dedupe_recommendation_duplicates`. Record which option
  was taken in `apply-progress.md`.
- **VERIFY**: B6, B7, B8 pass.

### B10. RED — dedupe runs before the 25-cap in `plan_recommendation_candidates`

- Add a failing test in `tests/test_application_recommendation_candidates.py`:
  a `scanned_records` fixture with more than 25 candidates where duplicates
  exist among the first 25 by scan order — assert the returned pool (after
  `plan_recommendation_candidates`) contains no duplicate-group collapses and
  that distinct-version tracks fill the 25 slots instead of the duplicates,
  for both the strategy and no-strategy branches.
- Requirement: Spec `recommendation-duplicate-version-dedupe` → "Duplicate
  versions collapse to one representative" and the "20-track pool" live
  regression scenario; design.md 3c placement requirement.

### B11. GREEN — call dedupe before `build_recommendation_pool`

- In `plan_recommendation_candidates`, after the optional
  `prefilter_strategy_candidates` call and before `build_recommendation_pool`,
  insert `pool_source = dedupe_recommendation_duplicates(pool_source,
  controls)` for both the strategy and no-strategy branches (per design.md
  3c's code sketch).
- **VERIFY**: B10 passes.

### B12. RED — anchor/energy filters still apply to surviving representatives

- Add a failing test: a pool with a duplicate group where dedupe removes a
  non-control candidate; generate under `same_color_energy`; assert the
  surviving representative is still subject to the same color/energy
  filtering as any other non-control candidate (no bypass introduced by
  dedupe).
- Requirement: Spec `recommendation-duplicate-version-dedupe` → "Anchor/energy
  filters apply to deduped representatives".

### B13. VERIFY — B12 passes; REFACTOR pass over Slice B

- Confirm B12 passes with the B9/B11 implementation as-is (no anticipated
  production change — the filter chain runs on the same `pool_source` object
  dedupe returns). Refactor for clarity/naming only if warranted; no logic
  change. Re-run B6-B12 plus `test_application_recommendation_candidates.py`.

### B14. Characterization — duplicate-free libraries unchanged end-to-end

- Add/confirm a test: a fixed pool of tracks and anchor with no duplicate
  groups produces an identical ordered candidate list, transition scores, and
  warnings before/after Slice B, under `same_color`, `same_energy`,
  `same_color_energy`.
- Requirement: Spec `recommendation-duplicate-version-dedupe` →
  "Duplicate-Free Libraries Are Unchanged" / "No duplicates means no change";
  "Strategy Filtering Semantics Are Unaffected" / "Filtering output is
  unchanged for duplicate-free pools".

### B15. VERIFY — Slice B full gate

- Run `uv run pytest -q`, `uv run pyright src tests`,
  `uv run pytest --cov --cov-fail-under=70 -q`, `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run python scripts/release_gate_check.py --run`.
- Confirm `tests/test_library_filter.py` is unmodified from its pre-Slice-B
  state (diff check) and still green.
- Confirm no `recommendation/` module imports anything from `desktop/`.

**Slice B parallelism**: B1 (baseline) must run first. B2/B3 (neutral module)
and the eventual B9 dedupe function are independent of each other in code but
B9 conceptually reuses B3's sort-key helper, so B3 must land before B9. B4/B5
(library_filter delegation) can be developed in parallel with B6-B9 (dedupe
function) since they touch different files, but both depend on B3. B10/B11
(wiring into `plan_recommendation_candidates`) depends on B9 being GREEN.
B12-B14 are verification tasks depending on B11. Recommended solo-implementer
order: B1 → B2 → B3 → B4 → B5 → B6 → B7 → B8 → B9 → B10 → B11 → B12 → B13 →
B14 → B15.

### Slice B — Review Workload Forecast

- **Estimated changed lines**: ~260-340 (additions + deletions), across new
  `library/duplicate_grouping.py` (~60-80 lines incl. docstrings),
  `library_filter.py` delegation refactor (~20-30 lines changed, mostly
  deletions replaced by thin calls), `candidate_pool.py` new
  `dedupe_recommendation_duplicates` (~35-50 lines), `recommendation_candidates.py`
  (~3-5 lines), optional `controls.py` promotion (~10-15 lines if taken), and
  tests (~130-180 lines: `test_duplicate_grouping.py` new,
  `test_library_filter.py` unmodified/zero, `test_candidate_pool.py` new,
  `test_application_recommendation_candidates.py` extended).
- **Chained-PR recommendation**: Ship as **PR2**, targeting the PR1 (Slice A)
  branch in the chain (Feature Branch Chain: PR1 → feature branch, PR2 →
  PR1's branch). Independently revertible; no functional dependency on
  Slice A's edits (disjoint files), but delivered second per the design's
  stated split.
- **400-line budget risk: Medium** (estimate sits below 400 but the new
  module + relocation + dedupe + full test surface together are the larger
  of the two slices; a promoted `controls.py` change or broader test coverage
  could push it close to budget).
- **Decision needed before apply: No** (design.md already resolves placement,
  algorithm, and the optional-promotion fallback; the only open call —
  promote vs. inline `preserved_control_paths` — has a documented default and
  a safe fallback, not a blocking decision)
- **Chained PRs recommended: Yes** (this is PR2 of the 2-slice chain)

---

## Combined Review Workload Forecast

- **Estimated changed lines (both slices combined)**: ~350-480
  (additions + deletions across production + tests).
- **Chained-PR recommendation**: Two chained PRs in a **Feature Branch
  Chain** — PR1 (Slice A: UI, targets the feature/tracker branch) → PR2
  (Slice B: pool dedupe, targets PR1's branch). This matches design.md's
  explicit recommended split and keeps each individual PR's diff inside the
  400-line budget even though the combined total may exceed it.
- **400-line budget risk: Medium** (combined total likely exceeds 400; each
  individual slice is designed to stay under or near budget on its own —
  Slice A Low, Slice B Medium — so the risk is at the combined-total level,
  not per-PR)
- **Decision needed before apply: No** (the chained-PR structure and slice
  boundaries are already fixed by design.md and this task breakdown; no
  further human decision is required to start Slice A)
- **Chained PRs recommended: Yes**

---

## Cross-slice notes

- Slice A and Slice B touch disjoint files and have **no technical ordering
  dependency** on each other; the "Slice A first" sequencing is a delivery
  choice (natural PR split from proposal.md/design.md), not a blocking
  dependency. A different chain order would work functionally, but this
  breakdown follows the design's stated recommendation.
- Every RED task must be run and confirmed **failing** before its paired
  GREEN task is implemented (`uv run pytest -q <path>::<test>` showing a
  failure), per strict TDD mode.
- No task in either slice touches audio files, DSP, real-time waveform
  analysis, or Serato V2 database writes.
- `apply-progress.md` (produced during `sdd-apply`) must record: (a) which
  preserve-set option was taken for B9 (promote vs. inline), and (b) the
  final actual changed-line counts per slice against this forecast.
