# Apply Progress: Tighten Spectral Color Filters — Slice A

Branch: `fix/same-color-energy-all-colors` → base `feat/tighten-spectral-color-filters` (tracker)
Chain strategy: feature-branch-chain. Review budget: 400 changed lines.
Mode: Strict TDD.

## Scope delivered (Phase 0 + Slice A + version bump)

Slice B (`same_color` dedicated bounded filter) is explicitly OUT of scope and untouched.

## TDD Cycle Evidence

| Task | RED (test written first) | GREEN (implementation) | REFACTOR |
|------|--------------------------|------------------------|----------|
| Phase 0 inventory (0.1–0.3) | Inventoried existing predecessor coverage; confirmed already-green safety net | No new tests needed — existing coverage suffices | Recorded suffices-list, no duplication |
| 1.1 per-colour admit (RED/GREEN/BLUE) | `test_same_color_energy_eligible_admits_proximate_rgb_candidate[RED/GREEN/BLUE]` failed on import (COLOR_* missing) | Delete early return + rename constants | — |
| 1.1 per-colour reject beyond L1 | `test_same_color_energy_eligible_rejects_rgb_candidate_beyond_rgb_l1[...]` | GREEN | — |
| 1.2 inclusive bound + just-over | `test_..._rgb_l1_at_inclusive_bound`, `test_..._rgb_centroid_and_rolloff_at_inclusive_bounds`, `test_..._rgb_rejects_each_bound_plus_epsilon[centroid/rolloff × colour]` | GREEN | Single-band L1 perturbation to avoid FP overshoot |
| 1.3 fail-closed per colour | `test_..._rgb_fails_closed_on_missing_profile / _zero_rgb_sum / _zero_denominator / _non_finite_ratio` (× RED/GREEN/BLUE) | GREEN | — |
| 1.4 delete MIXED-only early return | driven RED by 1.1–1.3 | Deleted `if anchor_profile.dominant_color != "MIXED": return True` (playlist_service.py) | — |
| 1.5 constant-name assertion | `test_color_gate_constants_are_colour_neutral_with_unchanged_values` | GREEN | — |
| 1.6 rename constants + refs | driven RED by import failure | Renamed 3 constants + 3 refs in `_mixed_profile_close`; updated comment/docstrings | — |
| 1.7 rename in tests | applied in test imports + MIXED boundary block | GREEN | — |
| 1.8 predecessor artifact rename | — | `tighten-same-color-energy/design.md:47,92` renamed coherently (name only) | — |
| 1.9 description verify | — | `strategies.py:116` unchanged (wording still true; verbatim test green) | — |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command + result | `uv run pytest tests/test_playlist_service.py -q -k "same_color_energy or constant or color_gate"` → **56 passed, 85 deselected** |
| Runtime harness | Phase 4 offscreen scratch-DB calibration (task 4.1/4.2) is a calibration acceptance-gate measurement, not a code blocker; constants stay provisional. **Deferred** — recorded here and in verify-report as an acceptance gate, not run in this apply batch (no live/scratch DB available in this environment). |
| Rollback boundary | Reverting the early-return deletion + the COLOR_* rename restores predecessor behaviour without touching `same_color`. Test-helper centroid/rolloff additions revert with the source. Version bump + uv.lock revert independently. |

## Blast-radius fixes beyond the task line-pointers

`SpectralProfile` defaults `centroid_hz=rolloff_hz=0.0`. Once RGB anchors flow
through the gate, every test helper that built RGB tracks with zero features
fails closed. Fixed at the root:

- `tests/test_playlist_service.py::spectral_track` — added `centroid_hz=1000.0, rolloff_hz=2000.0`.
- `tests/test_application_recommendation_candidates.py::_spectral_record` — same.
- `tests/test_candidate_pool.py::_spectral_record` — same.

`same_color` (label-only via `_apply_color_filter`) is unaffected by centroid/rolloff, so the out-of-scope `same_color` tests stay green.

Also removed a stray untracked `.DS_Store` that tripped `test_publication_artifact_hygiene` (macOS Finder artifact, never tracked, unrelated to this change).

## Six-command verification (exact order)

| # | Command | Result |
|---|---------|--------|
| 1 | `uv run pytest -q` | **1440 passed** |
| 2 | `uv run pyright src tests` | **0 errors, 0 warnings, 0 informations** |
| 3 | `uv run pytest --cov --cov-fail-under=70 -q` | **1440 passed, 91.19% coverage** |
| 4 | `uv run ruff check .` | **All checks passed!** |
| 5 | `uv run ruff format --check .` | **277 files already formatted** |
| 6 | `uv run python scripts/release_gate_check.py --run` | **PASS** (all gates; wheel/sdist built as 1.7.2) |

## Review budget

Authored code + tests + version bump + predecessor-doc rename = **~293 changed lines** (additions+deletions), within the 400 budget. Planning artifacts (proposal/design/spec/tasks) are pre-written provenance carried with the PR, not authored-code review burden.

## Tasks status

- Phase 0: 0.1 ✅ 0.2 ✅ (nothing missing) 0.3 ✅
- Phase 1 (Slice A): 1.1 ✅ 1.2 ✅ 1.3 ✅ 1.4 ✅ 1.5 ✅ 1.6 ✅ 1.7 ✅ 1.8 ✅ 1.9 ✅ 1.10 ✅
- Phase 3 (version): 3.1 ✅ (1.7.1 → 1.7.2) 3.2 ✅ (`uv lock`, only version changed)
- Phase 4 (offscreen harness): 🔲 deferred as calibration acceptance gate (see Work Unit Evidence)
- Phase 5 verification: 5.1 ✅
- Phase 2 (Slice B): see the Slice B section below.

---

# Apply Progress: Tighten Spectral Color Filters — Slice B

Branch: `fix/same-color-bounded-gate` → base `fix/same-color-energy-all-colors` (PR #336, slice A)
Chain strategy: feature-branch-chain. Review budget: 400 changed lines.
Mode: Strict TDD.

## Scope delivered (Phase 2 Slice B + version bump 1.7.2 → 1.7.3)

`same_color` gets its OWN bounded colour gate rather than widening the shared
helper. It now fails closed. Slice A (`same_color_energy` gate) is untouched.

## TDD Cycle Evidence

| Task | RED (test written first) | GREEN (implementation) | REFACTOR |
|------|--------------------------|------------------------|----------|
| 2.1 declared exception | `test_apply_same_color_filter_empty_strict_pool_fails_closed` failed on import (`_apply_same_color_filter` missing) | Added `_apply_same_color_filter` (fails closed) | — |
| 2.2 declared exception | `test_apply_same_color_filter_admits_only_candidates_inside_the_gate` failed on import (`_same_color_eligible` missing) | Added `_same_color_eligible` (bounded gate) | — |
| 2.3 per-colour gate | `test_same_color_eligible_*` (admit/reject-L1/inclusive-bounds/bound+epsilon/other-label/missing-profile/zero-sum/zero-denominator) × RED/GREEN/BLUE/MIXED | GREEN via `_same_color_eligible` reusing `_mixed_profile_close` | — |
| 2.4 energy still weighted | `test_same_color_eligible_ignores_energy_level`, `test_same_color_candidate_outside_anchor_energy_still_recommended` | GREEN (no energy branch in predicate) | — |
| 2.5 controls preserved | `test_same_color_preserves_controls_that_fail_the_gate` | GREEN (preserve_paths always survive) | — |
| 2.6 helpers | driven RED by 2.1–2.5 | `_same_color_eligible` + `_apply_same_color_filter` + `_same_color_warnings` | — |
| 2.7 dispatch rewire | driven RED by end-to-end tests | Removed `_COLOR_FILTER_STRATEGIES`; `same_color` branch at both call sites | — |
| 2.8 description verify | verbatim strategy-description test green | `strategies.py:102` unchanged (already true) | — |
| 2.9 dead-code removal | full suite green after removal | Removed `_apply_color_filter`, `_resolve_anchor_color`, `_track_color`; kept `_dominant_color_value` | Verified call graph before removing |
| 2.10 same_genre net | `test_apply_genre_filter_fallback_and_warnings_are_byte_identical` | GREEN (helper byte-unchanged) | — |
| re-authored 6 predecessor same_color e2e tests | RED after dispatch rewire | Re-authored to new bounded-gate/fail-closed contract | Docstrings record the reason |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command + result | `uv run pytest tests/test_playlist_service.py -q -k "same_color and not energy"` → **56 passed, 134 deselected** |
| Runtime harness | Phase 4 offscreen scratch-DB calibration (4.1/4.2) is a calibration acceptance gate, not a code blocker. **Deferred** — no live/scratch DB in this environment; constants stay provisional. Recorded here and in tasks.md. |
| Rollback boundary | Reverting the `feat(recommendation)` commit restores `same_color` to `_apply_color_filter` and re-adds the removed helpers, independent of slice A. Version bump + uv.lock revert independently via the `chore(release)` commit. |

## Fate of `_apply_color_filter` (task 2.9 — call-graph verified)

Verified against the real call graph BEFORE removing anything:
- `_apply_color_filter` was called ONLY at the two `_COLOR_FILTER_STRATEGIES`
  dispatch sites (`recommend_playlist`, `prefilter_strategy_candidates`). Both
  were rewired to `_apply_same_color_filter`, so the helper became genuinely
  orphaned → **removed**.
- `_resolve_anchor_color` was called only by `_apply_color_filter` → **removed**.
- `_track_color` was called only by `_apply_color_filter`/`_resolve_anchor_color`
  → **removed**.
- `_dominant_color_value` is ALSO called by `_resolve_same_color_energy_anchor`
  (slice A's live path) → **KEPT**.
- `_apply_genre_filter` is the genre path (`same_genre`), explicitly out of scope
  → **byte-unchanged**.

## Untouched strategies still pass byte-identically

Full suite green (1489 passed). `same_genre`'s `_apply_genre_filter` unfiltered
fallback + exact warning strings pinned directly and end-to-end; `same_energy`
`±1` band + verbatim description; `same_color_energy` (slice A) full behaviour;
`harmonic_journey`/`warmup`/`build`/`peak_time`/`chill`/`same_vibe` registered
descriptions; Camelot independence and `_dominant_color()` classification — all
unchanged.

## Declared characterization exception — WIDER than the prompt stated

The prompt named two `_apply_color_filter_*` tests. SIX MORE predecessor
end-to-end `same_color` characterization tests (`:295-381`) pinned the same
deliberately-replaced contract (the `same_color filter applied: {color}` warning,
label-only admission, unfiltered fallback). They could not stay green and were
re-authored (not deleted) to the new contract, each with a docstring recording
why. Flagged as a deviation in tasks.md per reporting discipline.

## Six-command verification (exact order)

| # | Command | Result |
|---|---------|--------|
| 1 | `uv run pytest -q` | **1489 passed** |
| 2 | `uv run pyright src tests` | **0 errors, 0 warnings, 0 informations** |
| 3 | `uv run pytest --cov --cov-fail-under=70 -q` | **1489 passed, 91% coverage** |
| 4 | `uv run ruff check .` | **All checks passed!** |
| 5 | `uv run ruff format --check .` | **277 files already formatted** |
| 6 | `uv run python scripts/release_gate_check.py --run` | **PASS** all gates (built as 1.7.3), exit 0 |

## Review budget — over 400, declared size:exception

Authored changed lines vs base `fix/same-color-energy-all-colors`: source
`playlist_service.py` **99+ / 60−** (159), tests `test_playlist_service.py`
**388+ / 41−** (429), `pyproject.toml` 1, `uv.lock` 1 → **~590 authored changed
lines**, OVER the 400 budget. The overflow is entirely per-colour test coverage
(RED/GREEN/BLUE/MIXED × admit/reject/inclusive/epsilon/label/fail-closed axes) for
one atomic work unit — the dedicated `same_color` filter and its tests, which the
work-unit rule keeps together. It cannot split further without separating a filter
from its own coverage. Recorded as an accepted **`size:exception`** under the
maintainer's `auto` mandate to complete the whole change; the strategy split (A/B)
was the planned chaining.

## Tasks status (Slice B)

- Phase 2 (Slice B): 2.1 ✅ 2.2 ✅ 2.3 ✅ 2.4 ✅ 2.5 ✅ 2.6 ✅ 2.7 ✅ 2.8 ✅ 2.9 ✅ 2.10 ✅ 2.11 ✅
- Phase 3 (version): 3.1 ✅ (1.7.2 → 1.7.3) 3.2 ✅ (`uv lock`, only version changed)
- Phase 4 (offscreen harness): 🔲 deferred as calibration acceptance gate
- Phase 5 verification: 5.1 ✅
