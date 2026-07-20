# Apply Progress: Same Color & Energy Strategy

Status: all 13 tasks complete. Single-slice apply, no chaining needed.

## Task-by-task log

- **Task 1 — CHARACTERIZE** (`tests/test_playlist_service.py`): added
  `test_same_color_output_and_warnings_are_stable_after_seam_widening` and
  `test_same_energy_output_and_warnings_are_stable_after_seam_widening`
  authored and run FIRST, before any production edit. Both passed
  immediately (baseline capture), confirming exact ordered paths and warning
  text:
  - `same_color`: `["/anchor.flac", "/red-a.flac", "/red-b.flac"]`,
    `["same_color filter applied: RED"]`
  - `same_energy`: `["/anchor.flac", "/near_high.flac", "/near_same.flac",
    "/near_low.flac"]`, `["Filtered 2 track(s) outside same_energy energy
    tolerance"]`
  Re-verified byte-identical after every later production edit (Tasks 3, 7).

- **Task 2 — RED** (`tests/test_playlist_strategies.py`,
  `tests/test_application_strategy_catalog.py`): added
  `"same_color_energy"` to `EXPECTED_STRATEGIES`,
  `test_same_color_energy_registers_with_expected_profile`, and
  `test_list_strategy_catalog_includes_same_color_energy`. Confirmed RED (5
  failures: set-mismatch, missing-profile `ValueError`, missing catalog
  entry).

- **Task 3 — GREEN** (`src/xfinaudio/recommendation/strategies.py`): added
  `"same_color_energy"` to the `StrategyName` Literal and a
  `_STRATEGIES["same_color_energy"]` entry (D2 weights: harmonic=0.25,
  bpm=0.15, energy=0.30, tags=0.10, spectral=0.20; `energy_tolerance=1`; no
  `energy_range`/`bpm_range`/`sort_hint` override). Confirmed GREEN (34
  passed across the two registration/catalog test files). Task 1
  characterization tests re-run: still PASS byte-identical (additive-only
  registration, no dispatch touched).

- **Task 3b — RED+GREEN** (guarantee-explicit descriptions): added
  `test_strategy_descriptions_state_guarantees` (substring checks). RED
  confirmed for the two existing profiles' copy. GREEN: updated
  `same_energy` description to "Hard limit: only tracks within ±1 energy
  level of the anchor. Color is weighted but not limited." and `same_color` to "Hard
  filter: only tracks matching the anchor's spectral color. Energy is
  weighted but not limited." (`same_color_energy`'s description was already
  set to the final guarantee-explicit text in Task 3: "Hard filters: only
  tracks matching the anchor's color AND within ±1 energy level of the
  anchor."). Confirmed no other test file asserted the old literals via
  repo-wide `rg` search (none found).

- **Task 4 — REFACTOR** (`strategies.py`): collapsed multi-line description
  strings to single-line where they fit the 120-char limit (one entry kept
  wrapped in parens to stay under 120 chars); confirmed still green and
  ruff-clean.

- **Task 5 — VERIFY**: `tests/test_playlist_strategies.py` +
  `tests/test_application_strategy_catalog.py` = 34 passed; `pyright` on
  `strategies.py` + its test file = 0 errors.

- **Task 6 — RED** (`tests/test_playlist_service.py`): added 6 new
  `same_color_energy` tests (filters-to-anchor-color,
  enforces-energy-tolerance, composes-color-and-energy-simultaneously,
  preserves-control-paths, falls-back-on-empty-color-pool-with-named-warning,
  prefilter-applies-color-and-energy). Confirmed RED: 5 of 6 failed (the
  control-preservation test passed trivially since energy_tolerance already
  activates automatically and, with no color filter running yet, all
  candidates pass through unfiltered — expected per design, still counts as
  RED for the overall task since the color/energy-composition assertions
  failed).

- **Task 7 — GREEN** (`src/xfinaudio/recommendation/playlist_service.py`):
  - Added `_COLOR_FILTER_STRATEGIES: frozenset[str] = frozenset({"same_color",
    "same_color_energy"})` near `MAX_ADJACENT_BPM_DIFFERENCE_PERCENT`.
  - Widened both `strategy.name == "same_color"` checks (in
    `recommend_playlist` and `prefilter_strategy_candidates`) to
    `strategy.name in _COLOR_FILTER_STRATEGIES`.
  - Added a `strategy_name: str` parameter to `_apply_color_filter`; both
    call sites now pass `strategy.name`.
  - Interpolated `strategy_name` into both `_apply_color_filter` warning
    lines (`"{strategy_name} filter applied: ..."` and
    `"{strategy_name}: no candidates match anchor color ..."`).
  - Interpolated `strategy.name` into the `_apply_energy_tolerance` warning
    (`"Filtered {removed} track(s) outside {strategy.name} energy
    tolerance"`).
  Confirmed GREEN: all 6 focused tests passed (after fixing one test-authoring
  bug — comparing `track.path` instead of `track.title`, since the local
  `track()` helper in this test file sets `title` to the filename including
  extension, unlike the `_track()` helper in `test_playlist_strategies.py`).
  Re-ran Task 1's characterization tests: still PASS byte-identical — proof
  the widened seam and warning interpolation reproduce prior literal text
  exactly for `same_color`/`same_energy`.

- **Task 8 — REFACTOR** (`playlist_service.py`): reviewed frozenset placement
  and parameter threading against the existing genre-filter style (consistent
  name-equality-then-membership dispatch, warnings-list return convention);
  wrapped one call site across three lines to stay under the 120-char ruff
  limit. Full `tests/test_playlist_service.py` suite: 48 passed.

- **Task 9 — VERIFY**: `test_playlist_service.py` +
  `test_playlist_strategies.py` + `test_application_strategy_catalog.py` = 82
  passed; `pyright` on `playlist_service.py`, `strategies.py`, and their test
  file = 0 errors.

- **Task 10 — VERIFY**: repo-wide `rg` confirmed `"same_color filter
  applied"`, `"same_color:"`, and `"outside same_energy"` are asserted only
  in `tests/test_playlist_service.py` — no other file needed updating for
  these specific warning strings.

- **Task 11 — VERIFY**: confirmed `list_strategy_catalog()` and
  `BuildViewModel.available_strategies()` remain registry-driven with zero
  edits to `src/xfinaudio/application/strategy_catalog.py` or
  `src/xfinaudio/desktop/build_view_model.py` (`git status --short` on both
  files is empty). `test_list_strategy_catalog_includes_same_color_energy`
  is the executable proof.

- **Task 12 — VERIFY**: `uv run pyright src tests` → 0 errors, 0 warnings.

- **Task 13 — VERIFY (full suite)**: see "Verification tail results" below.

## Unplanned but required fix (discovered during Task 13 full-suite run)

`tests/test_main_window.py::test_main_window_constructs_desktop_scanning_skeleton`
hardcoded `strategy_combo.count() == 9`. This is not one of the two
warning-text literals covered by Task 10 (that check was scoped to warning
strings, and correctly found no other hits) — it is a dropdown item-count
assertion, an expected and direct consequence of the new strategy
auto-enumerating through `list_strategy_catalog()` (Task 11's success
criterion). Updated the assertion to `== 10`. Confirmed via `rg` that no
other test asserts a combo-box count or an `available_strategies()` length
tied to the pre-change strategy count.

## Verification tail results

- `uv run pytest -q` → **1136 passed** (0 failed).
- `uv run pyright src tests` → **0 errors, 0 warnings, 0 informations**.
- `uv run pytest --cov --cov-fail-under=70 -q` → **1136 passed**; total
  coverage **90.69%** (well above the 70% floor);
  `src/xfinaudio/recommendation/strategies.py` at **100%**;
  `src/xfinaudio/recommendation/playlist_service.py` at **94%** (uncovered
  lines are pre-existing, unrelated to this change).
- `uv run ruff check .` → **All checks passed!**
- `uv run ruff format --check .` → **264 files already formatted**.
- `uv run python scripts/release_gate_check.py --run` → all gates **PASS**
  (coverage, lint, format, release readiness smoke, open-source publication
  docs, publication artifact hygiene, source package hygiene, PyInstaller
  check-only, root artifact hygiene). No `build/`/`dist/` artifacts created
  at the project root.

## Measured diff size

`git diff --stat -- src tests`:

```
 src/xfinaudio/recommendation/playlist_service.py |  19 +-
 src/xfinaudio/recommendation/strategies.py       |  14 +-
 tests/test_application_strategy_catalog.py       |   8 +
 tests/test_main_window.py                        |   2 +-
 tests/test_playlist_service.py                   | 141 +++++++++++
 tests/test_playlist_strategies.py                |  23 ++
 6 files changed, 196 insertions(+), 11 deletions(-)
```

**207 total changed lines** — under the 400-line review budget and under the
~260–300 forecast. No chained-PR split required.

## Deviations from design/spec

None. Implementation matches design.md D1–D6 exactly:
- D1: frozenset membership dispatch (Route A), selected as specified.
- D2: weights adopted verbatim.
- D3: `strategy_name`/`strategy.name` interpolation in all three warning
  producers, proven byte-identical for existing strategies via Task 1's
  regression guard.
- D4: empty-pool fallback exercised via color mismatch only; energy-empty
  remains terminal (no new energy fallback added).
- D5: `StrategyName` Literal extended; `pyright` confirms no exhaustiveness
  break.
- D6: all 7 test-plan items implemented as described.

## Next recommended phase

`sdd-verify` — implementation is complete, all tasks checked off, and all
verification-tail commands pass.
