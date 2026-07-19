# Design: Recommendation/Scoring Engine Correctness Fixes

## Decision question

How do we fix four correctness issues in the recommendation engine without introducing regressions or scope creep, given two of the four require a genuine product decision rather than a pure bugfix?

## Alternatives considered (Arbor-style)

### F1 — Camelot wrap-around

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Reuse `camelot.py::_camelot_move`'s circular-distance formula inline in `candidate_pool.py` | Matches the already-correct, already-tested logic exactly; minimal diff. | `candidate_pool.py` keeps its own independent key-comparison instead of importing the shared helper. | **Selected.** |
| B. Import and call `_camelot_move` from `candidate_pool.py` | No logic duplication. | `_camelot_move` and `_Move` are private (underscore-prefixed) to `camelot.py`; would require making them public API, a larger surface-area change than this fix warrants. | Rejected — out of proportion for a bugfix. |

### F3 — Manual→generated BPM seam

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Exempt manual tracks from the gate (keep current behavior) | Zero risk; respects explicit user track placement. | The seam can silently contain a musically "impossible" jump the gate is specifically designed to prevent everywhere else. | Rejected — user decision during grill. |
| B. Apply the same gate, seeded with the last manual track as anchor | Consistent behavior across every seam in the playlist, matching how `start_path` already works. | Requires branch-specific placement (see below) since the two sequencing branches reach "final order" at different pipeline stages. | **Selected** — user decision during grill. |

Branch placement sub-decision (found via Codex Round 1 adversarial review): the optimizer branch's pre-existing gate call (`playlist_service.py:114`) runs on the *unordered candidate pool*, before `recommend_sequence` decides final adjacency — seeding it there does not validate the true final seam. Fix: leave that pre-existing call untouched (out of scope) and add a second, new gate call after `sequenced.ordered_tracks` is known. The strategy-order branch needs no second call since its single existing gate already runs on the final order.

### F4 — Half-time/double-time BPM

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Full compatibility (normalize ratio before diffing) | Matches real DJ practice (half-time mixing is a standard technique); simplest change, reuses the one shared `_bpm_difference_percent` function used by both scoring and the jump gate. | No prior tolerance constant existed in this codebase for this kind of ratio check — introduces a new judgment-call constant. | **Selected** — user decision during grill. |
| B. Partial-credit compatibility (fixed intermediate score) | Reflects that half-time mixing isn't identical to same-tempo mixing. | Adds a third scoring tier with no existing precedent or requested threshold; more speculative than the ask. | Rejected — user decision during grill. |
| C. Out of scope | No new judgment calls. | Leaves a real, verified gap unresolved. | Rejected — user decision during grill. |

### Process — SDD/OpenSpec artifacts for this change

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. `PLAN.md`/`PLAN-REVIEW-LOG.md` only (the `/grill-me-codex` workflow's own artifacts) | Matches the entry-point skill's own contract; avoids process overhead for a small fix. | `AGENTS.md`/`openspec/config.yaml` `sdd.phase_rules` require proposal/spec/design/tasks/apply/verify for non-trivial changes; this change alters production recommendation-engine behavior, not just docs. Codex (Round 1 and Round 2 adversarial review) flagged this as a real governance gap, not a style nit. | Rejected on reconsideration. |
| B. Add the OpenSpec artifacts directly (this document set), authored from the already-locked `PLAN.md` content, without invoking the full `sdd-propose`/`sdd-spec`/`sdd-design`/`sdd-tasks` subagent pipeline | Satisfies `AGENTS.md`'s stated requirement; `PLAN.md`/`PLAN-REVIEW-LOG.md` are kept as the grill+adversarial-review audit trail (a superset, not a replacement). | Some duplication between `PLAN.md` and these files. | **Selected** — user decision after Codex raised it twice. |

## Architecture impact

- `candidate_pool.py::_camelot_compatible` — comparison logic only; no signature change.
- `camelot.py::score_camelot_transition` — docstring only; no behavior change.
- `playlist_service.py` — two sequencing branches gain conditional manual-anchor seeding of the existing `_drop_generated_tracks_after_impossible_bpm_jumps` gate; no new public functions.
- `scoring.py::_bpm_difference_percent` — internal normalization step added before the existing percent-difference formula; same signature, same callers (`_score_bpm` in this module, and `playlist_service.py` via import) benefit automatically.

## Affected files

- `src/xfinaudio/recommendation/candidate_pool.py`
- `src/xfinaudio/recommendation/camelot.py`
- `src/xfinaudio/recommendation/playlist_service.py`
- `src/xfinaudio/recommendation/scoring.py`
- `tests/test_recommendation_presenter.py`
- `tests/test_playlist_service.py`
- `tests/test_transition_scoring.py`

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato Database V2 writes.
- All four fixes are pure logic/scoring changes with no I/O or external side effects.

## Known pre-existing issue noted but not addressed here

`openspec/config.yaml`'s `project.root` field points to `/Users/freddymolina/Documents/audio`, a different, independent git checkout — the same class of stale-absolute-path issue already fixed in `AGENTS.md` and README.md test counts in a prior session (see engram memory `discovery/docs-precision-audit-readme-agents-drift-found-and-fixed-via-grill-me-codex`). Out of scope for this change; flagged for a future fix.
