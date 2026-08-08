# Continue `tighten-same-color-energy`

## Resume point

Planning is at the design gate. Exploration, proposal, delta specification, and a fourth design revision exist. **No production or test implementation has started, and no test pass is claimed.** The fourth design correction (authorized) is complete: it specifies the combined-strategy service wiring, marks MIXED thresholds calibration-provisional coherently across all four artifacts, binds the path-level anchor tiebreak identically everywhere, and names the shared-helper compatibility constraint and characterization gaps. Before creating `tasks.md`, satisfy every condition in the Tasks-gate below and re-run a fresh phase-contract validation.

## Objective and verified evidence

Make `same_color_energy` deliver its advertised strict spectral-color and energy guarantee without changing `same_color` or `same_energy`.

Saved playlist database row **id 43**, named **`same_color_energy - 20260802-115821`**, was verified against the library database:

| Evidence | Count |
|---|---:|
| Tracks | 16 |
| `dominant_color=MIXED` | 16 |
| Energy E8 | 9 |
| Energy E7 | 7 |
| Camelot 12A | 3 |

**Reproduction of these counts.** The counts above were produced by a READ-ONLY comparison of the saved-playlist row against the library database:

- Playlist database: the saved-playlists store used by the desktop app (the SQLite file holding saved-playlist rows, e.g. under `~/.xfinaudio/`).
- Library database: `~/.xfinaudio/xfinaudio.sqlite3` (the read-only scratch copy used for calibration; never the live DB while the app is running).
- Query shape (read-only): resolve the tracks referenced by playlist row `id 43` (`same_color_energy - 20260802-115821`), join each to its library record, then group-count by `dominant_color`, `energy_level`, and Camelot key over that track set. The anchor identity that produced the strict-comparison view is the resolved `same_color_energy` anchor path (start-path, else first manual-prefix record carrying the majority manual color, else first profiled record).
- Capture date: 2026-08-02 (from the playlist name timestamp `20260802-115821`).

Exact absolute file paths of the two databases on the capture machine are not recorded here; reproduce by running the read-only group-count above against the local `~/.xfinaudio/` databases on the same branch/checkout. Do not run counts against a live, app-open database.

The old implementation still satisfied its written contract. The product mismatch came from two permissive rules: `MIXED == MIXED` treated a broad residual spectral bucket as one cohesive color, and `energy_tolerance=1` accepted E7/E8/E9 around an E8 anchor. Camelot was not the defect; it is a separate harmonic score/gate.

## Product and safety decisions

Rule-shape and safety decisions below are settled. The MIXED numeric bounds are PROVISIONAL pending listening calibration (see "Decisions still requiring confirmation"); listening calibration cannot run before implementation exists, so freezing the numbers now would force reopening four artifacts later.

| Topic | Decision | Status |
|---|---|---|
| Energy | Generated candidates must exactly equal the resolved anchor's integer energy. | Settled |
| RED/GREEN/BLUE | Exact dominant-label equality only, plus exact energy. No continuous spectral threshold. | Settled |
| MIXED | Label equality is necessary but insufficient: a bounded anchor-relative gate over cached RGB L1, centroid delta, and rolloff delta, expressed as named constants `MIXED_RGB_L1_MAX` (initial `0.08`), `MIXED_CENTROID_REL_MAX` (initial `0.15`), `MIXED_ROLLOFF_REL_MAX` (initial `0.15`). Rule SHAPE settled; numeric values PROVISIONAL pending calibration. | Rule shape settled; numbers provisional |
| Camelot | Remains independent; keep existing harmonic scoring and transition gates. Do not require the anchor key. | Settled |
| Empty/invalid pool | Fail closed. Never silently widen to unfiltered candidates. | Settled |
| Controls | Locked, start, end, and manual controls are preserved user-owned exceptions and may violate generated-candidate constraints. | Settled |
| Compatibility | `same_color` and `same_energy`, including their fallbacks/warnings, remain unchanged. The shared `_apply_color_filter()` unfiltered fallback and warning text for `same_color` must not change. | Settled |
| Warnings | Explain missing anchor prerequisites, zero eligible candidates, and request shortages. Prefilter/context planning stays warningless; `recommend_playlist()` owns request-aware warnings. | Settled |
| Non-goals | No DSP, new analysis, schema migration, RMS hard filter, exact-key filtering, audio mutation, or live Serato DB V2 writes. | Settled |

MIXED profiles require finite RGB ratios with a positive sum and finite positive centroid/rolloff. Relative delta is `abs(candidate-anchor)/anchor`; zero or invalid denominators fail closed. RMS is excluded because mastering gain makes it unsuitable as a hard constraint.

## Anchor identity contract

Bind one immutable `anchor_path` from the same pre-anchor pool used by current `same_color`:

```text
full library
  -> completeness filter
  -> shared strategy/range filters
  -> requested-genre filter
  -> resolve anchor path: start_path -> first manual-prefix record carrying the majority manual color -> first profiled record
  -> strict combined filter
  -> dedupe while protecting anchor identity
  -> candidate cap while retaining anchor identity
  -> final defensive enforcement with the same bound path
```

- Locked controls never select the anchor; they are output exceptions only.
- Anchor identity must be stable before the strict filter, dedupe, and cap.
- Never re-resolve after dedupe/capping: a duplicate sibling could replace the first-profile anchor.
- A supplied missing/invalid bound path fails closed and is not replaced.

## Compatibility seam and resolved design blocker

The exported `plan_recommendation_candidates(...) -> list[TrackRecord]` contract must remain list-returning for all callers. Add a separate internal context seam, such as frozen `RecommendationCandidateContext(records, same_color_energy_anchor_path)`, used only by the desktop `same_color_energy` route.

The prior blocker — that `RecommendationService` had no way to reach a `MainWindow` context method — is now RESOLVED in the fourth design revision (`design.md`, Data Flow section). Verified against the checkout: `RecommendationService.recommend()` (`src/xfinaudio/desktop/recommendation_service.py:148-167`) calls only `self._desktop_recommendation_records(controls, strategy_name)` at line 164 and has no context callback today; the fix adds one via the existing injection discipline. The design now specifies all of the following, so this section is a record of closure, not an open task:

1. A typed combined-strategy context callback parameter added to `RecommendationService.set_actions()` (`recommendation_service.py:102-125`).
2. Stored on `RecommendationService` initialized to `_unwired` in `__init__` (`recommendation_service.py:46-67`), matching the existing sentinel discipline.
3. Injected from `src/xfinaudio/desktop/window_service_wiring.py` in `wire_main_recommendation_service()` (lines 91-102) as `desktop_same_color_energy_candidate_context=self._desktop_same_color_energy_candidate_context`.
4. Invoked **only** when `strategy_name == "same_color_energy"`; ordinary strategies continue through `_desktop_recommendation_records()`.
5. A wiring/dispatch regression in `tests/test_recommendation_service_state.py` proving combined-only invocation and ordinary-path compatibility.

No unresolved architecture blocker remains. The only outstanding item is post-implementation threshold calibration (an acceptance gate, not a design blocker), enumerated in "Decisions still requiring confirmation".

## Design-gate history

| Attempt | Result | What it fixed or found |
|---|---|---|
| 1 — initial design | Failed with four bounded issues | Found that continuous centroid/rolloff validity must apply only to MIXED; an uncontrolled first-profile anchor could change during dedupe/cap; locked controls must remain exceptions rather than anchors; and shortage warnings cannot be computed in prefiltering because request size is unavailable. |
| 2 — automatic correction | Failed with two remaining blockers | Fixed MIXED/RGB rules, immutable anchor protection, locked-control semantics, and request-aware warning ownership. Validation then found that the anchor was not explicitly bound from the exact current `same_color` pool and the proposed context transport risked replacing the public list-returning planner contract. Automatic mode stopped after this second failed gate. |
| 3 — explicitly authorized correction | Failed with one remaining blocker | Fixed anchor binding after completeness/shared/requested-genre filters and preserved the public list API through a separate internal context planner. Validation found the missing `RecommendationService.set_actions()` and `window_service_wiring.py` callback injection path. |
| 4 — authorized correction | Resolved the wiring blocker; provisional-threshold and evidence coherence | Specified the typed/`_unwired`-stored/injected/dispatch-guarded `desktop_same_color_energy_candidate_context` callback and its regression test; added `window_service_wiring.py` to design File Changes; replaced `Open Questions: None` with the truthful state. Marked MIXED numeric bounds calibration-provisional coherently across proposal/spec/design/CONTINUATION while keeping the bounded-gate rule shape and geometry evidence normative. Bound the path-level anchor tiebreak identically across design/spec/CONTINUATION. Named the shared `_apply_color_filter()` compatibility constraint and the untested `_apply_energy_tolerance()` characterization gap. Made the tasks-gate checklist enforce named conditions. |

## Repository and artifact inventory

- Branch: `codex/fix-same-color-energy-semantics`, HEAD `b71afa2` (verified via `git rev-parse --short HEAD`).
- Complete worktree status at capture (verified via `git status --porcelain`):

  ```text
   D AGENTS.md
  ?? .agents/
  ?? openspec/changes/tighten-same-color-energy/
  ```

  This includes the tracked deletion ` D AGENTS.md` (previously omitted), plus the untracked `.agents/` directory and the untracked change directory. To reproduce, run `git status --porcelain` from the repository root on this branch.

| Artifact | Status |
|---|---|
| `exploration.md` | Complete; verified cause, feasibility, and recommended approach. |
| `proposal.md` | Complete; modified capability contract. |
| `specs/same-color-energy-strategy/spec.md` | Delta spec present; includes strict eligibility, controls, warnings, Camelot independence, and corrected anchor precedence. |
| `design.md` | Fourth revision present; service callback wiring specified completely, no unresolved architecture blocker. |
| `CONTINUATION.md` | This handoff. |
| `tasks.md`, `state.yaml`, `apply-progress.md`, `verify-report.md` | Not created. |

Relevant implementation/test paths already identified:

- `src/xfinaudio/recommendation/strategies.py`
- `src/xfinaudio/recommendation/playlist_service.py`
- `src/xfinaudio/recommendation/candidate_pool.py`
- `src/xfinaudio/application/recommendation_candidates.py`
- `src/xfinaudio/application/playlist_workflow.py`
- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/recommendation_service.py`
- `src/xfinaudio/desktop/window_service_wiring.py`
- `tests/test_playlist_strategies.py`
- `tests/test_playlist_service.py`
- `tests/test_application_recommendation_candidates.py`
- `tests/test_recommendation_service_state.py`

## Tasks-gate (all conditions MUST be checkable and checked before `tasks.md` is created)

Advancing to `tasks.md` is BLOCKED until every named condition below is true. Do not tick a box on prose alone; each condition names an artifact section that must contain the stated content.

- [ ] **Wiring specified.** `design.md` Data Flow section specifies the combined-context callback as (a) typed in `RecommendationService.set_actions()`, (b) `_unwired`-initialized in `__init__`, (c) injected from `window_service_wiring.py`, and (d) dispatch-guarded to `strategy_name == "same_color_energy"`. Verify the four items are present.
- [ ] **Wiring test specified.** `design.md` Testing Strategy names the wiring/dispatch regression in `tests/test_recommendation_service_state.py` proving combined-only invocation AND ordinary-path compatibility.
- [ ] **File Changes complete.** `design.md` File Changes table contains a row for `src/xfinaudio/desktop/window_service_wiring.py`.
- [ ] **No implied blockers.** `design.md` Open Questions enumerates any remaining blocker explicitly (currently: none architecture-level; only post-implementation threshold calibration). A blocker that is implied but not enumerated fails this gate.
- [ ] **Characterization safety net named.** `design.md` Testing Strategy requires characterization of current `same_color`/`same_energy` behavior — the `+/-1` energy band from `_apply_energy_tolerance()` and the shared `_apply_color_filter()` unfiltered fallback/warning — BEFORE any change.
- [ ] **Thresholds coherent.** MIXED numeric bounds are marked calibration-provisional named constants in proposal, spec, design, and CONTINUATION, with no `Approved` framing contradicting the pending-calibration status.
- [ ] **Anchor tiebreak identical.** The path-level tiebreak ("first manual-prefix record carrying the majority manual color") is stated identically in design, spec, and CONTINUATION.

Only after ALL boxes are checked:

- [ ] Re-run fresh phase-contract validation; stop if any blocker remains.
- [ ] Create `tasks.md` with a Review Workload Forecast; enforce the 400-changed-line guard and choose a chain/exception only if required.
- [ ] Implement every behavior change through strict **RED -> GREEN -> REFACTOR**, starting with characterization of unchanged strategies and controls.
- [ ] Cover threshold boundaries, invalid MIXED profiles, anchor stability through dedupe/cap, requested-genre ordering, public list API compatibility, combined-only callback dispatch, shortages, and fail-closed behavior.
- [ ] Validate offscreen against a scratch copy of the real library database, never the live DB; inspect pool sizes, warnings, and boundary examples across multiple anchors.
- [ ] Perform listening calibration around the thresholds. This remains an acceptance gate, not a completed validation.
- [ ] Run the full repository verification sequence without skipping or reordering:

```bash
uv run pytest -q
uv run pyright src tests
uv run pytest --cov --cov-fail-under=70 -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/release_gate_check.py --run
```

## Decisions still requiring confirmation

1. **Threshold acceptance:** the MIXED numeric bounds are calibration-provisional named constants — evidence-based for playlist 43 but not frozen. Listening calibration across multiple real-library anchors must confirm them before acceptance, and calibration cannot run before implementation exists. A post-calibration change touches only the named constant definitions and must be reflected coherently in proposal/spec/design/tests.
