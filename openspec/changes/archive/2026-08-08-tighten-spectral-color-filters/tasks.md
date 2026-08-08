# Tasks: Tighten Spectral Color Filters

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~360-430 (source ~90, tests ~230, specs already written, artifact ref renames ~15, version+lock ~10) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (slice A) → PR 2 (slice B) |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

Per-file estimate: `playlist_service.py` ~90 (delete early return, rename 5 refs, add `_same_color_eligible` + `_apply_same_color_filter` + `_same_color_warnings`, rewire two dispatch sites, drop `same_color` from `_COLOR_FILTER_STRATEGIES`); `strategies.py` ~0-2 (descriptions already match, verify only); `tests/test_playlist_service.py` ~230 (rename refs, re-author 2 characterization tests, per-colour gate tests for two strategies, fail-closed + energy-still-weighted + controls tests); predecessor artifact ref renames ~15; `pyproject.toml` +1, `uv.lock` regenerated. Honest total is at the 400 line, driven by per-colour test coverage across two strategies — over budget once both delta specs count. Split along strategy lines per design §Implementation Envelope.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| A | `same_color_energy` gate spans all colours + colour-neutral rename | PR 1 | `uv run pytest tests/test_playlist_service.py -q -k "same_color_energy or constant"` | Offscreen scratch-DB run driving `same_color_energy` across MIXED/RED/GREEN/BLUE (task A.6) | Removing the `!= "MIXED"` deletion + reverting the constant rename restores predecessor behaviour without touching `same_color` |
| B | `same_color` dedicated bounded filter + fail-closed | PR 2 | `uv run pytest tests/test_playlist_service.py -q -k "same_color and not energy"` | Offscreen scratch-DB run driving `same_color` across all colours (task B.7) | New `_same_color_eligible`/`_apply_same_color_filter`/`_same_color_warnings` + dispatch rewire are removable; restoring `same_color` to `_apply_color_filter` reverts independently of slice A |

feature-branch-chain base boundaries: PR 1 base = `feat/tighten-spectral-color-filters` (tracker); PR 2 base = PR 1 branch. If PR 2 shows PR 1's diff, rebase before review.

## Phase 0: Safety Net — Characterize What Must NOT Change (do FIRST, all colours)

- [x] 0.1 RED — inventory existing predecessor coverage: identify which `tests/test_playlist_service.py` tests already pin `same_energy`'s `±1` band + verbatim description, `same_genre`'s `_apply_genre_filter` unfiltered fallback + exact warning strings, and the registered descriptions of `harmonic_journey`/`warmup`/`build`/`peak_time`/`chill`/`same_vibe`. Record the test names that already suffice; do NOT duplicate them. `tests/test_playlist_service.py`.
- [x] 0.2 RED — where the blast radius of THIS change reaches an untouched strategy without existing coverage, add a characterization test asserting byte-identical behaviour: `same_genre` warning strings compared exactly, `same_energy` ordered candidates + description compared exactly. Only add what 0.1 proved missing. `tests/test_playlist_service.py`.
- [x] 0.3 GREEN — confirm the full safety-net suite is green on the pre-change tree before any behaviour change: `uv run pytest tests/test_playlist_service.py -q`.

## Phase 1: Slice A — `same_color_energy` gate spans all colours (RED → GREEN → REFACTOR)

- [x] 1.1 RED — add per-colour gate tests for `same_color_energy` via `_same_color_energy_eligible`: for RED, GREEN and BLUE anchors, a same-label same-energy candidate inside the gate is admitted; one whose anchor-relative RGB L1 exceeds the bound is rejected. `tests/test_playlist_service.py`.
- [x] 1.2 RED — inclusive-boundary + just-over cases per colour (RED/GREEN/BLUE): candidate exactly at `COLOR_RGB_L1_MAX`, `COLOR_CENTROID_REL_MAX`, `COLOR_ROLLOFF_REL_MAX` is eligible; each bound + epsilon on its own axis is rejected. `tests/test_playlist_service.py`.
- [x] 1.3 RED — fail-closed per colour: missing/non-finite RGB ratios, non-positive RGB sum, and zero/non-finite centroid or rolloff denominator each reject the candidate for RED/GREEN/BLUE anchors (not only MIXED). `tests/test_playlist_service.py`.
- [x] 1.4 GREEN — delete the `if anchor_profile.dominant_color != "MIXED": return True` early return at `playlist_service.py:852-853` so the bounded gate applies to every dominant-colour label. `src/xfinaudio/recommendation/playlist_service.py`.
- [x] 1.5 RED — assert no `MIXED_`-prefixed gate constant remains and that `COLOR_RGB_L1_MAX`/`COLOR_CENTROID_REL_MAX`/`COLOR_ROLLOFF_REL_MAX` exist with unchanged values `0.08`/`0.15`/`0.15`. `tests/test_playlist_service.py`.
- [x] 1.6 GREEN — rename constants `MIXED_RGB_L1_MAX`→`COLOR_RGB_L1_MAX`, `MIXED_CENTROID_REL_MAX`→`COLOR_CENTROID_REL_MAX`, `MIXED_ROLLOFF_REL_MAX`→`COLOR_ROLLOFF_REL_MAX` at `playlist_service.py:58-60` and every reference (`:824`, `:828`, `:831`). `src/xfinaudio/recommendation/playlist_service.py`.
- [x] 1.7 GREEN — move the rename into the test imports/refs at `tests/test_playlist_service.py:7-9` and `:1480-1532`. `tests/test_playlist_service.py`.
- [x] 1.8 GREEN — propagate the rename coherently into predecessor artifacts so `ruff`/`pyright` and predecessor tests stay green: `openspec/changes/tighten-same-color-energy/design.md:47,92` (any other in-repo `MIXED_*` gate-constant references surfaced by search). Do NOT alter the predecessor's frozen behaviour, only the constant name. `openspec/changes/tighten-same-color-energy/design.md`.
- [x] 1.9 REFACTOR — verify `same_color_energy` description at `strategies.py:116` still matches behaviour (label + exact energy + gate); adjust only if wording drifted. `src/xfinaudio/recommendation/strategies.py`.
- [x] 1.10 VERIFY (slice A) — `uv run pytest tests/test_playlist_service.py -q -k "same_color_energy or constant"`, then full `uv run pytest -q`.

## Phase 2: Slice B — `same_color` bounded colour gate, no energy limit, fails closed (RED → GREEN → REFACTOR)

- [x] 2.1 RED (declared characterization exception) — re-authored `test_apply_color_filter_same_color_falls_back_to_unfiltered_pool` → `test_apply_same_color_filter_empty_strict_pool_fails_closed`: empty strict pool returns preserved controls only, never the unfiltered library. Reason in test docstring. `tests/test_playlist_service.py`.
- [x] 2.2 RED (declared characterization exception) — re-authored `test_apply_color_filter_same_color_keeps_matching_candidates` → `test_apply_same_color_filter_admits_only_candidates_inside_the_gate`: same-label candidate admitted only inside the gate, rejected beyond `COLOR_RGB_L1_MAX`. Reason in test docstring. `tests/test_playlist_service.py`.
- [x] 2.3 RED — per-colour gate tests for `same_color` (RED/GREEN/BLUE/MIXED) via `_same_color_eligible`: label equality + inside-gate admitted; outside-gate rejected; inclusive-boundary eligible; each bound + epsilon rejected; other-label rejected; degenerate profile / zero denominator / zero RGB sum fails closed for every colour. `tests/test_playlist_service.py`.
- [x] 2.4 RED — energy-still-weighted assertion: `test_same_color_eligible_ignores_energy_level` (predicate) + `test_same_color_candidate_outside_anchor_energy_still_recommended` (end-to-end). Both prove a different-energy candidate stays eligible for `same_color`. `tests/test_playlist_service.py`.
- [x] 2.5 RED — controls preserved: `test_same_color_preserves_controls_that_fail_the_gate`. `tests/test_playlist_service.py`.
- [x] 2.6 GREEN — added `_same_color_eligible` (label equality + `_mixed_profile_close`, NO energy branch), `_apply_same_color_filter` (mirrors `_apply_same_color_energy_filter`, no unfiltered fallback), and `_same_color_warnings` (prerequisite-missing + strict-empty). `src/xfinaudio/recommendation/playlist_service.py`.
- [x] 2.7 GREEN — rewired `same_color` dispatch off the shared helper: `_COLOR_FILTER_STRATEGIES` removed entirely; `same_color` branches added at both call sites (`recommend_playlist`, `prefilter_strategy_candidates`), shaped like the `same_color_energy` blocks minus energy/anchor transport. `_apply_genre_filter` byte-unchanged. `src/xfinaudio/recommendation/playlist_service.py`.
- [x] 2.8 GREEN — `same_color` description at `strategies.py:102` ("Hard filter … Energy is weighted but not limited.") is now true; unchanged (wording already matches). `src/xfinaudio/recommendation/strategies.py`.
- [x] 2.9 REFACTOR — call-graph verified: `_apply_color_filter` was called only at the two `_COLOR_FILTER_STRATEGIES` sites, both removed → orphaned → removed. `_resolve_anchor_color` (called only by `_apply_color_filter`) and `_track_color` (called only by those two) → removed. `_dominant_color_value` KEPT (still used by `_resolve_same_color_energy_anchor`). `_apply_genre_filter` is the genre path, out of scope, untouched. `src/xfinaudio/recommendation/playlist_service.py`.
- [x] 2.10 REFACTOR — `test_apply_genre_filter_fallback_and_warnings_are_byte_identical` asserts the `_apply_genre_filter` unfiltered fallback + exact warning strings directly; the existing end-to-end `same_genre` fallback test stays green. `tests/test_playlist_service.py`.
- [x] 2.11 VERIFY (slice B) — `uv run pytest tests/test_playlist_service.py -q -k "same_color and not energy"` → **56 passed, 134 deselected**; full `uv run pytest -q` → **1489 passed**.

## Phase 3: Release Gate — version bump + lock (both slices land)

- [x] 3.1 `chore(release)` — Slice A bumped `1.7.1 → 1.7.2`. Slice B bumps `1.7.2 → 1.7.3` above its own base branch `fix/same-color-energy-all-colors` (1.7.2). CI gate `Non-audio release gates` fails any PR whose version equals its base branch's; `release_gate_check.py` does NOT catch this locally, only CI does. `pyproject.toml`.
- [x] 3.2 Regenerated `uv.lock` (`uv lock`); `git diff uv.lock` shows only `1.7.2 → 1.7.3`. `uv.lock`.

## Phase 4: Offscreen End-to-End Harness (scratch DB, never live)

- [x] 4.1 DONE 2026-08-08 (was DEFERRED while no library was reachable) — `~/.xfinaudio/xfinaudio.sqlite3` was copied to `/tmp/xfin-calib/scratch.sqlite3` and every read ran against that scratch copy; the live DB was never opened. The sweep is a read-only pool-geometry measurement over the cached spectral profiles rather than an offscreen `MainWindow` run: the gate under test (`_spectral_profile_close` / `_color_eligible`, `playlist_service.py:804-851`) is a pure predicate over cached profile values, so driving it directly measures exactly what a UI run would have measured, with no Qt surface and no write path. Corpus: 10,367 tracks with `metadata_status = 'complete'` and a non-null spectral profile (of 10,392 total). Recorded in `verify-report.md` § Calibration Evidence.
- [x] 4.2 DONE 2026-08-08 (was DEFERRED) — Drove BOTH `same_color` and `same_color_energy` pools across MIXED, RED, GREEN and BLUE anchors: 40 anchors sampled per dominant-color label (seed 20260808), measuring pool sizes, per-axis pass rates, one-axis-dropped pools, per-axis bound sweeps, and the admitted L1 / centroid / rolloff spread. Outcome: **no pool collapse**; `COLOR_RGB_L1_MAX` is the binding axis for every colour; the two relative-delta bounds are near-saturated at `0.15`. `COLOR_RGB_L1_MAX = 0.08`, `COLOR_CENTROID_REL_MAX = 0.15`, `COLOR_ROLLOFF_REL_MAX = 0.15` are **RETAINED UNCHANGED** — no production source change results. Full evidence in `verify-report.md` § Calibration Evidence.

## Phase 5: Verification Sequence (final task — exact order, no skipping or reordering)

- [x] 5.1 Run, in this exact order, all passing (slice B, 1.7.3):
  ```bash
  uv run pytest -q                                    # 1489 passed
  uv run pyright src tests                            # 0 errors, 0 warnings
  uv run pytest --cov --cov-fail-under=70 -q          # 1489 passed, 91% coverage
  uv run ruff check .                                 # All checks passed!
  uv run ruff format --check .                        # 277 files already formatted
  uv run python scripts/release_gate_check.py --run   # PASS all gates (built as 1.7.3), exit 0
  ```

## Deviation from prompt scope (declared, per reporting discipline)

The slice B prompt named exactly TWO characterization tests as the declared
exception (`test_apply_color_filter_same_color_falls_back_to_unfiltered_pool`,
`test_apply_color_filter_same_color_keeps_matching_candidates`). In fact SIX MORE
end-to-end `same_color` characterization tests from the predecessor change
(`tighten-same-color-energy`, "Task 1: freeze same_color output/warnings before
dispatch is widened", `tests/test_playlist_service.py:295-381`) pinned the SAME
deliberately-replaced contract at the pipeline level — the `same_color filter
applied: {color}` warning, plain label-only admission, and the unfiltered
fallback. They cannot stay green: the warning no longer exists and the fallback is
gone by the maintainer's fail-closed decision. They fall under the identical
principle as the two named tests (a characterization test pinning the exact
behaviour being deliberately changed), so they were RE-AUTHORED (not deleted) to
the new bounded-gate / fail-closed contract, each with a docstring recording why.
The prompt's "only two tests" premise was inaccurate; flagged here rather than
followed blindly.
