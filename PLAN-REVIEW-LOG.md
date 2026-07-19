# Plan Review Log: Fix correctness bugs in the recommendation/scoring engine
Act 1 (grill) complete — plan locked with the user. MAX_ROUNDS=5.
Reviewer model: gpt-5.6-sol (config default, reasoning effort: low) — codex-cli 0.144.6.

## Round 1 — Codex

1. BUG — the optimizer-branch seam fix (PLAN.md step 3, original draft) seeds the gate at playlist_service.py:114, which runs on the unordered `remaining_tracks` BEFORE `recommend_sequence` decides final adjacency. Fix: seed the *finalized* `sequenced.ordered_tracks` instead.
2. "Applied identically at both call sites" is not implementable — the two branches have different data flow. Fix: give branch-specific pseudocode.
3. Planned test only covers `warmup` (strategy-order branch) — cannot catch the optimizer-branch defect above. Fix: add a second test for an optimizer strategy (e.g. `harmonic_journey`).
4. Plan omits mandatory SDD/TDD lifecycle work per AGENTS.md ("every non-trivial change produces durable artifacts under openspec/"). Fix: add OpenSpec proposal/spec/design/tasks/state artifacts and RED-first task ordering.

VERDICT: REVISE

### Claude's response
- Findings 1-3: verified against the actual code (playlist_service.py:103-130) — confirmed real. The optimizer branch's existing gate at line 114 runs on `remaining_tracks` pre-sequencing; seeding it there doesn't validate true final adjacency once `recommend_sequence` reorders everything. Rewrote PLAN.md step 3: strategy-order branch keeps a single combined gate call (its `sequenced_tracks` is already final order); optimizer branch gets a NEW second gate call after `sequenced.ordered_tracks` is known, with its own distinct warning/count rather than merging into the pre-existing count (merging would misreport which stage dropped a track). Added a second test (optimizer branch, `harmonic_journey` + `manual_order_paths`) since one test can no longer cover both now-different code paths.
- Finding 4: partially accepted. Rejected the full OpenSpec artifact pipeline (proposal/spec/design/tasks/state.yaml) as disproportionate scaffolding for a 4-item bug-fix plan that the user routed through `/grill-me-codex` (not `/sdd-propose`) — PLAN.md/PLAN-REVIEW-LOG.md already serve the same durable-record purpose for this workflow. Accepted the RED-first TDD spirit of the finding: build must write each test first, confirm it fails, then implement the fix — logged as a non-negotiable build constraint given this session's Strict TDD Mode.

## Round 2 — Codex

- Prior findings 1-3 (optimizer placement, branch-specific logic, dual test coverage) and RED-first ordering: addressed.
- Prior finding 4 (OpenSpec lifecycle): NOT addressed — "the plan explicitly rejects repository governance rather than satisfying it."
- NEW BUG: the optimizer branch's new post-sequencing gate call validates the *entire* seeded chain (manual→gen1→gen2→...), not just the manual→gen1 seam, but every drop was labeled "at the manual→generated seam" — misleading, since deeper generated→generated drops could occur too. Fix: either restrict to a first-track-only check, or keep full-chain validation but use accurate, non-seam-specific wording.
- Repeated, more forceful: "`/grill-me-codex` does not override `AGENTS.md`... Workflow selection cannot silently waive repository-level governance." Cited `openspec/config.yaml`'s explicit phase_rules requiring proposal/spec/design/tasks for "feature/refactor work."

VERDICT: REVISE

### Claude's response
- New bug: verified — `_drop_generated_tracks_after_impossible_bpm_jumps` validates the whole seeded chain (confirmed via the function body and the existing `test_warmup_...` test, which already drops 2 tracks in a row from a single anchor, proving this function was never "seam-only" to begin with). Fixed PLAN.md: removed the invented "at the manual→generated seam" wording, replaced with the same generic warning phrasing already used elsewhere in the file — an honest description ("the same anchor-validation gate applied with the manual track as the anchor") instead of a narrower claim the code doesn't actually make true.
- OpenSpec governance: reconsidered seriously rather than defaulting to my Round 1 rejection again. Verified `openspec/config.yaml`'s `sdd.phase_rules` do explicitly require proposal/spec/design/tasks/apply/verify for "feature/refactor work," and confirmed `openspec/changes/` is genuinely active for this repo (real prior commits reference it, e.g. `project-audit-remediation`). Concluded my Round 1 rationale (workflow choice waives repo governance) doesn't hold — AGENTS.md carves out no such exception, and I had already treated AGENTS.md as authoritative earlier this session when fixing its own stale-path bug. Given this is a process/governance call rather than a code-correctness call, surfaced it to the user directly instead of unilaterally re-deciding it a second time. User chose: add the OpenSpec artifacts now, authored directly from PLAN.md's already-locked content (not via the full sdd-propose/sdd-spec/sdd-design/sdd-tasks subagent pipeline). Created `openspec/changes/recommendation-scoring-correctness-fixes/{proposal,spec,design,tasks}.md` + `state.yaml`.

## Round 3 — Codex

- Optimizer gate placement, full-chain warning accuracy, both-branch tests: addressed.
- OpenSpec lifecycle: mostly addressed, but incomplete — `apply-progress.md` and `verify-report.md` missing from the change folder even as placeholders.
- Optimizer test description (PLAN.md, step 3 test bullet) still said "assert the seam-specific warning fires," contradicting the just-revised generic-wording implementation two paragraphs above it.

VERDICT: REVISE

### Claude's response
- Both accepted, no scope concerns — pure internal-consistency fixes. Created `apply-progress.md` and `verify-report.md` placeholders in the change folder (status: pending, to be filled in during apply/verify). Fixed PLAN.md's optimizer test bullet to reference the generic warning text and `post_sequencing_dropped_count`, matching the implementation section it was describing.

## Round 4 — Codex

- Missing apply-progress.md/verify-report.md, contradictory seam-specific warning assertion, required OpenSpec artifact set: all addressed/complete.
- NEW: F4's test plan only covers exact ratio=2.0 (128/64) and an obviously-non-2:1 pair (128/100) — an equality-only (`ratio == 2.0`) implementation would pass both, never exercising the tolerance band the fix promises. Fix: add cases just inside/outside the 2% boundary, both argument directions.
- NEW: state.yaml reports `step: design` while design AND tasks are both marked complete and `next_recommended: apply` — internally contradictory, could misroute lifecycle automation.

VERDICT: REVISE

### Claude's response
- Both accepted — legitimate test-coverage and metadata-consistency gaps, no scope concerns. Added boundary test cases to PLAN.md step 4 (verified the exact numbers via Python: ratio 1.97 → 128 vs 64.97 inside the [1.96, 2.04] band, ratio 1.95 → 128 vs 65.64 outside it, both directions). Fixed state.yaml's `step` field from `design` to `tasks` (the actual last-completed phase, matching `next_recommended: apply`).

## Round 5 — Codex

(First attempt hung past the skill's 10-minute ceiling and was stopped per the skill's own hard rule — treated as a failed run, not retried blind. User asked for one retry; retry completed normally.)

- Tolerance-boundary coverage, stale lifecycle phase: addressed.
- NEW: if both the pre-sequencing gate and the new post-sequencing (manual-seam) gate drop tracks in the same call, both append the identical generic warning text — indistinguishable, defeating the Round 2 rationale for keeping separate counters ("merging would misreport which stage dropped a track" — identical unlabeled messages have the same problem).
- NEW: `tasks.md` task 8 still only mentions exact-ratio and non-2:1 cases, not the boundary cases added to PLAN.md in Round 4 — the durable task artifact is out of sync with the reviewed plan.

VERDICT: REVISE

## MAX_ROUNDS reached — deadlock, handed to user
Per the skill's hard rule ("the loop ALWAYS terminates at MAX_ROUNDS"; do not fake convergence), this is a genuine deadlock, not a false APPROVED. Both Round 5 findings are legitimate on inspection but minor (an observability/wording gap, not a correctness bug; and a documentation-sync gap, not a code gap). Claude's assessment: both are worth fixing before build, but neither warrants burning another Codex round given the hard cap — surfaced to the user for a decision on how to close them out.

### User decision
Fix both directly (no further Codex round), then proceed to build.

### Resolution
- Warning-message finding: fixed. Post-sequencing (manual-seam) warning now reads "...relative to the manually ordered tracks", distinguishing it from the pre-sequencing warning's plain text. Added a dual-drop test to PLAN.md step 3.
- tasks.md sync finding: fixed. Task 7 now mentions the dual-drop test; task 8 now mentions the tolerance-boundary cases from PLAN.md step 4.

Status: **DEADLOCKED at MAX_ROUNDS=5, resolved by user decision + Claude fixes (not by Codex APPROVED).** Proceeding to Act 3 build on this basis, per the user's explicit sign-off.

## Act 3 — Build (Claude, direct implementation)

Implemented tasks 4-9 of `openspec/changes/recommendation-scoring-correctness-fixes/tasks.md`,
following PLAN.md's already-corrected code exactly (not design.md's simplified
summary), with RED-first TDD per this session's Strict TDD Mode.

### F1 — Camelot wrap-around (`candidate_pool.py::_camelot_compatible`)

RED: added `test_build_pool_treats_camelot_wrap_around_as_compatible` to
`tests/test_recommendation_presenter.py` — a `12A` anchor with a `1A` candidate and
a genuinely-incompatible `6A` candidate; confirmed the wrap-around candidate did
NOT rank ahead of the incompatible one before the fix (both fell into the same
"incompatible" key bucket and tie-broke alphabetically by path).
GREEN: replaced the raw `abs(track_num - anchor_num) <= 1` comparison with the
same circular-distance calculation already used by `camelot.py::_camelot_move`
(`min(direct_delta, 12 - direct_delta)`).

### F2 — Camelot docstring (`camelot.py::score_camelot_transition`)

Doc-only fix, no test required. Replaced the stale `"diagonal fuzzy 0.7"` claim
with `"diagonal (adjacent number, different letter) 0.9"`, matching the code's
real, already-tested behavior. Verified `tests/test_camelot_scoring.py` (5 tests)
stayed green — confirms no code path was touched.

### F3 — Manual→generated BPM seam (`playlist_service.py`)

Implemented both branches exactly as corrected during adversarial review:
- Strategy-order branch: single combined gate call, seeded with
  `manual_prefix[-1]` when present, keeping the existing (unsuffixed) warning text.
- Optimizer branch: left the pre-existing pre-sequencing gate at
  `remaining_tracks` untouched; added a new second gate call after
  `sequenced_tracks = sequenced.ordered_tracks`, seeded with `manual_prefix[-1]`,
  using the Round-5-corrected warning text with the
  `" relative to the manually ordered tracks"` suffix so the two stages are
  text-distinguishable when both fire in the same call.

RED: added three tests to `tests/test_playlist_service.py` — strategy-order
(`warmup` + `manual_order_paths`), optimizer-branch (`harmonic_journey` +
`manual_order_paths`), and a dual-drop case where the pre-sequencing gate and the
new post-sequencing gate each drop a different track in the same
`recommend_playlist` call. Confirmed all three failed before the production fix
(details in `apply-progress.md`'s TDD Cycle Evidence table). Note: the dual-drop
test's track ordering had to account for `harmonic_journey`'s default `sort_hint`
("path", alphabetical) applied during `_apply_strategy_filters` before controls
are resolved — this reorders `remaining_tracks` ahead of the pre-sequencing gate,
which the first draft of the test didn't account for and had to be corrected
during the build session itself (not by Codex).
GREEN: all three pass after the two-branch fix above.

### F4 — Half-time/double-time BPM (`scoring.py::_bpm_difference_percent`)

Added `HALF_TIME_RATIO_TOLERANCE = 0.02` and the ratio-normalization branch exactly
as specified in PLAN.md, including the Round-4-added tolerance-boundary logic.

RED: added four tests to `tests/test_transition_scoring.py` — exact 2:1 ratio
(both directions), a non-2:1 pair (unaffected-behavior check), and the two
tolerance-boundary cases (`128` vs `64.97` inside `[1.96, 2.04]`, `128` vs `65.64`
outside it, both directions). 2 of 4 failed before the fix (exact-ratio and
inside-boundary); the other 2 passed both before and after by design, since they
assert unchanged behavior.
GREEN: all four pass after the fix.

### Verification results

Full mandatory sequence from `AGENTS.md:58-63`, all green:

| Command | Result |
|---|---|
| `uv run pytest -q` | 1015 passed |
| `uv run pyright src tests` | 0 errors |
| `uv run pytest --cov --cov-fail-under=70 -q` | 1015 passed, 90.29% coverage |
| `uv run ruff check .` | all checks passed |
| `uv run ruff format --check .` | 263 files already formatted (one test file was auto-reformatted by `ruff format` for line width during the run — no logic change) |
| `uv run python scripts/release_gate_check.py --run` | PASS (exit 0) |

### Artifacts updated

- `openspec/changes/recommendation-scoring-correctness-fixes/tasks.md` — tasks
  4-9 checked off (task 10 "Archive" left unchecked, out of scope for this build).
- `openspec/changes/recommendation-scoring-correctness-fixes/apply-progress.md` —
  filled in with completed tasks and full TDD Cycle Evidence table.
- `openspec/changes/recommendation-scoring-correctness-fixes/verify-report.md` —
  filled in with verification command results and R1-R4 requirement evidence.
- `openspec/changes/recommendation-scoring-correctness-fixes/state.yaml` —
  `phases.apply: complete`, `phases.verify: complete`, `step: verify`,
  `next_recommended: review` (`phases.review` and archival left untouched, per
  scope).

Status: **Act 3 build complete.** All four fixes implemented RED-first, all
tests pass, full verification sequence green. Ready for review phase.

## Act 4 — Native review (Claude ↔ gentle-ai review, post-apply gate)

Per this repo's post-sdd-phase governance (AGENTS.md), ran the native
`gentle-ai review` lifecycle (4R lens set: risk, resilience, readability,
reliability — high risk tier, driven by native scope detection, not manual
selection). User confirmed proceeding with the full working-tree scope the
tool derived (which also bundled the earlier, separately-closed docs-precision
fix and two pre-existing untracked files, since native scope is
repository-wide, not task-scoped).

**Lineage 1 — `review-79e5d8dc8c1146b5`**: approved, 0 BLOCKER/CRITICAL, 6
non-blocking findings (2 resilience, 3 readability, 1 reliability — see
`openspec/changes/recommendation-scoring-correctness-fixes/apply-progress.md`
for full detail). User asked to fix all 6 and then archive.

**Corrections applied**: extracted `_bpm_jump_warning()` helper (fixes the DRY
finding and, by describing mechanism instead of claiming causal attribution,
both resilience findings at once); added branch-asymmetry comments; corrected
the `HALF_TIME_RATIO_TOLERANCE` comment to document the effective ±4% band;
added a test for `score_transition`'s explanation-string behavior on half-time
pairs.

**Lineage 2 — `review-27ab3f92fd4eeceb`** (re-review of the corrected content):
risk/resilience/readability confirmed clean. Reliability found a **new
CRITICAL**: `src/xfinaudio/quality/dj_readiness.py` had kept its own private,
unfixed duplicate of `_bpm_difference_percent`. The recommendation engine now
treats a 128↔64 BPM pair as fully compatible, but the DJ export-readiness
check still computed the pre-fix formula and would flag it "needs_review" with
a misleading "100.00% jump" message — a real cross-module inconsistency
directly caused by the F4 fix, missed because `quality/` was marked out of
scope at the grill and never re-checked for downstream consumers of the
formula being changed. This lineage was correctly **escalated** (native
governance requires stopping on a CRITICAL, not silently reopening the same
budget) once captured.

**Fix applied**: `dj_readiness.py` now imports the shared, half-time-aware
`_bpm_difference_percent` from `scoring.py` instead of maintaining its own
duplicate (deleted). Added
`test_dj_readiness_treats_half_time_bpm_pair_as_continuous` asserting both
modules now agree.

**Lineage 3 — `review-78d1fed3f42157d4`** (final): all 4 lenses re-ran against
the fully corrected content. Risk, resilience, readability: clean. Reliability
hand-traced the CRITICAL fix's arithmetic end-to-end and confirmed it resolved;
also grepped for further duplicates of the BPM-formula family and found a
*third* one in `src/xfinaudio/desktop/screens/live_assistant_screen.py`
(live-alert feature), but correctly classified it `causal_disposition:
base-only` — it predates this diff entirely and was not touched by it, so it
does not block. Logged as an explicit follow-up, not fixed here (out of scope
for this change; a pre-existing gap, not one this change introduced or
worsened). **Approved.** Receipt:
`.git/gentle-ai/review-transactions/v2/review-78d1fed3f42157d4/review-receipt.json`.

Final verification: 1017 tests passed (1015 after Act 3 + 2 more from the
native-review corrections), pyright 0 errors, ruff check/format clean.

Status: **Native review approved. Proceeding to archive.**
