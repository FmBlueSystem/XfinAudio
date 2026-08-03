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

- [ ] 2.1 RED (declared characterization exception) — re-author `test_apply_color_filter_same_color_falls_back_to_unfiltered_pool` (`tests/test_playlist_service.py:1369`) as a fail-closed test for the new `_apply_same_color_filter`: empty strict pool returns preserved controls only + explicit strict-colour warning, never the unfiltered library. Reason recorded in test docstring: this test pinned the exact fallback-to-unfiltered behaviour this change deliberately replaces — the sole legitimate characterization-edit exception per design §Testing Strategy. `tests/test_playlist_service.py`.
- [ ] 2.2 RED (declared characterization exception) — re-author `test_apply_color_filter_same_color_keeps_matching_candidates` (`tests/test_playlist_service.py:1392`) as a bounded-gate test: same-label candidate admitted only when inside the gate, rejected when outside `COLOR_RGB_L1_MAX`. Reason recorded in test docstring: it pinned plain label equality, the behaviour this change deliberately replaces with the bounded gate. `tests/test_playlist_service.py`.
- [ ] 2.3 RED — per-colour gate tests for `same_color` (RED/GREEN/BLUE/MIXED) via `_same_color_eligible`: label equality + inside-gate admitted; outside-gate rejected; inclusive-boundary eligible; each bound + epsilon rejected; degenerate profile / zero denominator fails closed for every colour. `tests/test_playlist_service.py`.
- [ ] 2.4 RED — energy-still-weighted assertion: a candidate that passes the bounded colour gate but whose `energy_level` differs from the anchor is STILL eligible for `same_color` (no energy check in the predicate). `tests/test_playlist_service.py`.
- [ ] 2.5 RED — controls preserved: locked/start/end/manual-prefix controls survive `_apply_same_color_filter` even when they fail the gate, in their positions. `tests/test_playlist_service.py`.
- [ ] 2.6 GREEN — add `_same_color_eligible(anchor, candidate) -> bool` (label equality + `_mixed_profile_close`, NO energy branch), `_apply_same_color_filter(...)` (mirrors `_apply_same_color_energy_filter`: preserved controls always survive, non-controls survive only on `_same_color_eligible`, no unfiltered fallback), and `_same_color_warnings(...)` (prerequisite-missing + strict-empty, never widens). `src/xfinaudio/recommendation/playlist_service.py`.
- [ ] 2.7 GREEN — rewire `same_color` dispatch off the shared `_apply_color_filter`: remove `same_color` from `_COLOR_FILTER_STRATEGIES` (`playlist_service.py:46`, leaving it empty), and add `same_color` branches at the two call sites (`:265` / `recommend_playlist` and `:691` / `prefilter_strategy_candidates`) shaped like the `same_color_energy` blocks, minus energy/anchor-path transport. Leave `_apply_color_filter` and `_apply_genre_filter` byte-unchanged. `src/xfinaudio/recommendation/playlist_service.py`.
- [ ] 2.8 GREEN — verify `same_color` description at `strategies.py:102` ("Hard filter … Energy is weighted but not limited.") is now true; change only if wording drifted. `src/xfinaudio/recommendation/strategies.py`.
- [ ] 2.9 REFACTOR — remove any dead code left by the `same_color` cut (e.g. `_apply_color_filter` now used by no strategy — confirm and remove if truly orphaned, or leave with a comment if `same_genre` still needs the shape; verify against `_apply_genre_filter` being the genre path). `src/xfinaudio/recommendation/playlist_service.py`.
- [ ] 2.10 REFACTOR — assert `same_genre`/`_apply_genre_filter` fallback and warning strings are byte-identical (safety net from Phase 0 must remain green). `tests/test_playlist_service.py`.
- [ ] 2.11 VERIFY (slice B) — `uv run pytest tests/test_playlist_service.py -q -k "same_color and not energy"`, then full `uv run pytest -q`.

## Phase 3: Release Gate — version bump + lock (both slices land)

- [x] 3.1 `chore(release)` — bump `version` in `pyproject.toml:3` above base `main` `1.7.1`. CI gate `Non-audio release gates` fails any PR whose version equals its base branch's; `release_gate_check.py` does NOT catch this locally, only CI does. `pyproject.toml`.
- [x] 3.2 Regenerate `uv.lock` (`uv lock`) so the project's own pinned version (`uv.lock:1477`) matches the bump. Confirm `git diff uv.lock` shows only the version change. `uv.lock`.

## Phase 4: Offscreen End-to-End Harness (scratch DB, never live)

- [ ] 4.1 Copy `~/.xfinaudio/xfinaudio.sqlite3` to a scratch path first (the app writes to whatever DB it opens — see `.agents/skills/verify`). Launch offscreen (`QT_QPA_PLATFORM=offscreen`, `MainWindow.with_defaults(db_path=DB_COPY, settings_path=SCRATCH_SETTINGS)`), pattern from `scripts/screenshot_app_with_colors.py`. NEVER open the live DB.
- [ ] 4.2 Drive `same_color_energy` AND `same_color` across MIXED, RED, GREEN and BLUE anchors: select anchor row → Build tab → set strategy combo (internal name) → `_sync_state()` → `recommend_button.click()` → poll `last_recommendation`. Reset between runs. For each colour × strategy, measure the admitted L1 spread and record pool sizes and warnings. This is a calibration acceptance-gate measurement, not a code blocker (constants stay provisional). Evidence goes to `verify-report.md`.

## Phase 5: Verification Sequence (final task — exact order, no skipping or reordering)

- [x] 5.1 Run, in this exact order, all passing:
  ```bash
  uv run pytest -q
  uv run pyright src tests
  uv run pytest --cov --cov-fail-under=70 -q
  uv run ruff check .
  uv run ruff format --check .
  uv run python scripts/release_gate_check.py --run
  ```
