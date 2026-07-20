# Verify Report: Strategy UX Clarity and Duplicate Dedupe

- **Change**: `strategy-ux-clarity-and-dedupe`
- **Artifact store**: openspec
- **Verified against**: merged `main` (PR #303 commit `e403482` Slice A;
  PR #304 commit `169022f` Slice B + delta + bounded correction)
- **Branch during verify**: `docs/verify-archive-strategy-ux` (read-only; no code changed)
- **Date**: 2026-07-19
- **Strict TDD**: active
- **Verdict**: **PASS WITH NOTES** — 0 CRITICAL, 3 WARNING (documentation
  alignment only), 1 SUGGESTION. All spec requirements satisfied by
  implementation + asserting tests; full verification tail green.

---

## 1. Verification tail (actual results on the merged tree)

| Command | Result |
|---|---|
| `uv run pytest -q` | **1201 passed** in ~27s |
| `uv run pyright src tests` | **0 errors, 0 warnings, 0 informations** |
| `uv run pytest --cov --cov-fail-under=70 -q` | **1201 passed**, total coverage **90.76%** (required 70%) |
| `uv run ruff check .` | **All checks passed!** |
| `uv run ruff format --check .` | **267 files already formatted** |
| `uv run python scripts/release_gate_check.py --run` | **exit 0 — all gates PASS** (coverage, lint, format, release readiness smoke, open-source publication docs, publication artifact hygiene, source package hygiene, PyInstaller check-only, root artifact hygiene) |

Targeted suite (`tests/test_build_screen.py tests/test_recommendation_service_state.py
tests/test_duplicate_grouping.py tests/test_candidate_pool.py
tests/test_application_recommendation_candidates.py tests/test_library_filter.py`):
**119 passed**.

---

## 2. Requirement-by-requirement trace

### Spec A — `strategy-selection-ux/spec.md`

| Requirement | Implementation (merged tree) | Asserting test | Status |
|---|---|---|---|
| Immediate Description Refresh on Selection | `_on_strategy_changed` slot connected to `currentIndexChanged` (`build_screen.py:273,415`) → `_refresh_strategy_explanation(vm)` (`:361`); `_last_vm` stored in `render()` (`:58,342`) | `test_build_screen.py::test_strategy_explanation_label_refreshes_immediately_on_selection_change` | PASS |
| Selector Shows Display Names | `addItem(option.display_name, option.name)` (`build_screen.py:311`) | `test_build_screen.py::test_strategy_combo_shows_display_names_and_stores_internal_name_as_data` | PASS |
| Downstream Consumers Keep Working | `recommend()` reads `currentData()` (`recommendation_service.py:145`); `on_recommend_requested` uses `findData` (`:224`); `_on_recommend` uses `currentData()` (`build_screen.py:412`) | `test_recommendation_service_state.py::test_recommend_reads_strategy_via_current_data`, `::test_on_recommend_requested_selects_item_via_find_data`, `test_build_screen.py::test_on_recommend_emits_internal_strategy_name_via_current_data` | PASS |
| Persisted/Exported Artifacts Record Internal Names | strategy persistence flows via `PlaylistStrategy.name` (internal), untouched by combo text | `test_build_screen.py::test_selecting_strategy_by_display_name_resolves_to_internal_strategy_name` | PASS |
| Filtering Semantics and Descriptions Unaffected | Slice A does not touch `strategies.py`/`playlist_service.py` | existing `test_playlist_strategies.py` / `test_playlist_service.py` byte-identical description + filtering guarantees | PASS |

Only residual `currentText()` is the defensive fallback `currentData() or
currentText()` in `_refresh_strategy_explanation` (`build_screen.py:362`),
explicitly allowed by design.md.

### Spec B — `recommendation-duplicate-version-dedupe/spec.md` (AMENDED — stricter playlist key)

| Requirement | Implementation (merged tree) | Asserting test | Status |
|---|---|---|---|
| Candidate Pool Keeps One Representative per Group (stricter playlist key; parenthetical descriptor content ignored) | `playlist_duplicate_group_key` + `normalize_title_for_playlist_grouping` (`duplicate_grouping.py:72,116`); `dedupe_recommendation_duplicates` groups via the playlist key (`candidate_pool.py:156`) | `test_candidate_pool.py::test_dedupe_collapses_too_hot_single_version_and_clean_verbatim_live_pair`, `::..._se_la_...`, `::..._still_...`, `::test_dedupe_all_three_live_pairs_collapse_in_one_pool`; `test_duplicate_grouping.py::test_playlist_duplicate_group_key_collapses_parenthetical_descriptor_variants` | PASS |
| ...Library display grouping is unchanged | `library_filter.py` delegates to conservative `normalize_title_for_grouping` / `duplicate_group_key(placeholder=_DASH)`; `tests/test_library_filter.py` zero edits | `test_library_filter.py` (39 tests, unmodified & green) + contrast test `test_duplicate_grouping.py::test_conservative_key_keeps_parenthetical_variants_distinct` | PASS |
| Control Tracks Never Removed by Dedupe | `preserved_control_paths(controls)` (`controls.py:83`); controls-in-group all survive (`candidate_pool.py:165-167`) | `test_candidate_pool.py::test_dedupe_keeps_locked_duplicate_and_removes_non_control_sibling`, `::..._start_...`, `::..._end_...`, `::..._manual_order_...`, `::test_dedupe_keeps_all_controls_when_multiple_controls_share_a_group` | PASS |
| Duplicate-Free Libraries Unchanged | order-preserving pass-through (`candidate_pool.py:183`) | `test_candidate_pool.py::test_dedupe_no_duplicates_is_byte_identical_and_order_preserving`, `::test_dedupe_free_pool_produces_identical_recommendation_across_strategies` | PASS |
| Representative Choice Deterministic | `duplicate_representative_sort_key` (`duplicate_grouping.py:141`), `min(...)` selection | `test_candidate_pool.py::test_dedupe_is_deterministic_across_repeated_runs`, `::test_dedupe_representative_choice_matches_documented_sort_key` | PASS |
| Strategy Filtering Semantics Unaffected | dedupe wired BEFORE `build_recommendation_pool` for both branches (`recommendation_candidates.py`); filters run on survivors | `test_candidate_pool.py::test_dedupe_survivor_is_still_filtered_by_anchor_color_under_same_color_energy`; `test_application_recommendation_candidates.py::test_plan_recommendation_candidates_dedupes_before_cap_{without,with}_strategy` | PASS |

Layering guard confirmed: no `recommendation/` module imports `desktop/`;
`duplicate_grouping.py` is Qt-free / desktop-free (AST test present).

---

## 3. Bounded correction (lineage `review-c8b72a193ac5d41f`) — two CRITICAL fixes CONFIRMED

Both native-4R CRITICAL findings are fixed and asserted in the merged tree:

1. **Incomplete record could silently eliminate a complete duplicate sibling.**
   `dedupe_recommendation_duplicates` now groups only
   `metadata_status == "complete"` records (`candidate_pool.py:153-155`, with
   the defect rationale in the docstring `:141-148`).
   Test: `test_application_recommendation_candidates.py::test_plan_recommendation_candidates_does_not_lose_complete_track_to_incomplete_locked_duplicate` (+ CRITICAL-1 note in `test_candidate_pool.py::test_dedupe_excluded_manual_path_is_not_treated_as_preserved`).
2. **Fully-parenthetical titles collided on an empty key.** Singleton guard in
   `playlist_duplicate_group_key` (`duplicate_grouping.py:132-137`): empty
   normalized title returns `None`.
   Tests: `test_duplicate_grouping.py::test_playlist_duplicate_group_key_none_when_normalized_title_is_fully_parenthetical`, `test_candidate_pool.py::test_dedupe_does_not_collapse_distinct_fully_parenthetical_titles`.

---

## 4. Task completion

- Slice A tasks **A1–A16**: all `[x]` in `tasks.md`; implementations match code state (combo display-name migration, `currentData`/`findData` reads, immediate-refresh slot, refactor helper).
- Slice B tasks **B1–B15**: all `[x]`; implementations match (neutral `duplicate_grouping.py`, `library_filter.py` delegation with zero test edits, `dedupe_recommendation_duplicates`, wiring before the 25-cap, `preserved_control_paths` promotion).
- Delta batch (playlist-level key) recorded in `apply-progress.md` and `state.yaml` with RED-before-GREEN evidence.
- RED-before-GREEN evidence present in `apply-progress.md` for Slice A, Slice B, and the delta batch.

---

## 5. Notes (recorded, NOT blocking — align at archive)

- **WARNING (traceability)**: `apply-progress.md` does **not** record the
  bounded-correction batch (the two CRITICAL fixes) with RED-before-GREEN
  evidence. That evidence lives only in commit `169022f`'s message and the
  `CRITICAL 1/2 correction (native 4R review)` test comments. The fixes and
  their tests are present and green in the merged tree; the SDD apply artifact
  is simply missing a correction-batch entry. Recommend adding it at archive.
- **WARNING (stale design)**: `design.md` still documents the conservative-key
  pool plan (`duplicate_group_key(r.title, r.artist, placeholder=None)` at
  `design.md:182`), superseded by the maintainer-decided
  `playlist_duplicate_group_key`. Known; to be aligned at archive.
- **WARNING (budget)**: `size:exception` accepted by maintainer 2026-07-20 for
  Slice B (post-delta 980 changed src+tests lines; production delta modest,
  overage is test coverage). Recorded in `state.yaml`; not blocking.
- **SUGGESTION**: consider splitting `test_candidate_pool.py` (320 lines) if it
  grows further; purely organizational.

---

## 6. Safety constraints

- No audio-file mutation, no DSP/rendering, no Serato V2 writes, no in-place
  `AppState` mutation introduced.
- No project-root `build/`/`dist/` artifacts (release-gate hygiene PASS).

## Verdict

**PASS WITH NOTES.** Both specs fully satisfied with asserting tests; all
verification commands green; both CRITICAL corrections present and tested.
Outstanding items are documentation-alignment only (design.md staleness,
apply-progress correction-batch entry) and the accepted size:exception —
resolve them in the archive phase.
