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
- Phase 2 (Slice B): 🔲 out of scope for this PR
