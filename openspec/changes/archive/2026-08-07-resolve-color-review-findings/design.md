# Design: Resolve Two-Axis Review Findings for Colour Strategies

## Decision question

The bounded colour gate runs **twice** — once in `prefilter_strategy_candidates` to
narrow the pool, once in `recommend_playlist` to enforce the final result. How do we
make both passes agree on one anchor without changing the public candidate-planning
contract, and how do we stop the two colour strategies drifting apart?

## Alternatives considered

### F2 — Carrying the bound anchor

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Return `RecommendationCandidateContext(records, color_anchor_path)` from a **new** `plan_recommendation_candidate_context`, leaving `plan_recommendation_candidates` returning a plain list | Only the colour strategies pay for the anchor; every other caller and strategy keeps the list contract byte-identical. `plan_recommendation_candidates` delegates for colour strategies, so the two cannot disagree. | Two planning entry points to keep in step. | **Selected.** |
| B. Change `plan_recommendation_candidates` to return the context for every strategy | One entry point. | Rewrites a public contract every caller depends on, for a value only two strategies read. | Rejected — out of proportion. |
| C. Put the anchor path on `DJControls` | Rides an existing seam. | `DJControls` models what the DJ asked for; the anchor is machine-bound identity. Conflating them makes the anchor look user-settable. | Rejected. |

### F2 — What a supplied-but-absent anchor path means

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Fail closed (`resolve_when_unbound=False` → drop every generated candidate) | Honest: the caller bound an identity and it is gone. An empty result plus a warning is a truthful answer. | A DJ sees an empty set. | **Selected** — the whole point of binding is that the gate cannot silently switch anchors. |
| B. Re-resolve from the current pool | Never empty. | Reintroduces exactly the bug: the final pass gates against a different anchor than the pool was narrowed for. | Rejected. |
| C. Widen to the unfiltered pool | Never empty. | A strategy whose registered description says "Hard filter" would return the whole library. | Rejected. |

`color_anchor_path=None` stays distinct from both: it means "nothing was bound",
so internal resolution runs as before. Absence and invalidity are different facts.

### F3 — Making room for the protected anchor

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Displace the last **trimmable** slot; if none exists, keep the pool and drop the anchor | Controls always survive; existing relative order is preserved. The no-trimmable-slot case degrades into the fail-closed behaviour the gate already has. | The anchor is silently absent in the all-controls case. | **Selected.** |
| B. Displace the last slot unconditionally | One line. | Can evict a control, which `apply_controls` then rejects downstream — trading a colour bug for a control bug. | Rejected (the finding). |
| C. Grow the pool by one | Nothing is evicted. | Breaks the cap the pool size exists to enforce. | Rejected. |

### F6 — Deduplicating the two colour strategies

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. A frozen `_ColorGate` record per strategy in a `_COLOR_GATES` map, consumed by one filter chain | `same_color_energy` IS `same_color` plus one predicate; the rest that differs is wording. Keeping the difference in **data** is what stops the two paths drifting. `COLOR_FILTER_STRATEGIES = frozenset(_COLOR_GATES)` then falls out as the single dispatch answer. | Indirection between strategy name and behaviour. | **Selected.** |
| B. Subclass or strategy-object hierarchy | Extensible. | Two members, one differing predicate — a class hierarchy costs more than it explains. | Rejected. |
| C. Leave the two copies, add a comment | Zero risk. | The drift the review found is exactly what two copies produce. | Rejected. |

### Process — SDD artifacts for this change

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Ship on the PR description alone | Fastest. | `AGENTS.md` requires durable `openspec/` artifacts for every non-trivial change; this one alters production recommendation behaviour across three packages. | Rejected on reconsideration. |
| B. Author the artifacts **retroactively** from the merged commit | Satisfies the requirement and documents what actually shipped, verifiable against `git show`. | Written after the fact, so they record rather than steer the work — stated plainly here rather than implied. | **Selected** — same precedent as `2026-07-18-recommendation-scoring-correctness-fixes`. |

## Architecture impact

- `recommendation/playlist_service.py` — `_ColorGate` + `_COLOR_GATES` + exported
  `COLOR_FILTER_STRATEGIES`; `_apply_color_filter` / `_color_eligible` /
  `_color_filter_warnings` / `_resolve_color_anchor` / `_anchor_meets_prerequisites`
  replace the per-strategy pair; new public `resolve_color_anchor_path`;
  `recommend_playlist` gains keyword-only `color_anchor_path`.
- `application/recommendation_candidates.py` — new `RecommendationCandidateContext`
  dataclass and public `plan_recommendation_candidate_context`;
  `plan_recommendation_candidates` delegates to it for colour strategies.
- `recommendation/candidate_pool.py` — `build_recommendation_pool`'s protected-path
  retention becomes control-aware; `dedupe_recommendation_duplicates` protects the anchor.
- `application/playlist_workflow.py` — `same_color_energy_anchor_path` renamed to the
  strategy-neutral `color_anchor_path` and forwarded.
- `desktop/` — `MainWindow._desktop_color_anchor_candidate_context` added, wired into
  `RecommendationService` through `window_service_wiring.py`; `recommend` routes colour
  strategies to it.

## Affected files

- `src/xfinaudio/application/playlist_workflow.py`
- `src/xfinaudio/application/recommendation_candidates.py`
- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/recommendation_service.py`
- `src/xfinaudio/desktop/window_service_wiring.py`
- `src/xfinaudio/recommendation/candidate_pool.py`
- `src/xfinaudio/recommendation/playlist_service.py`
- `tests/test_application_recommendation_candidates.py`
- `tests/test_candidate_pool.py`
- `tests/test_playlist_service.py`
- `tests/test_recommendation_service_state.py`

## Safety

- No audio mutation, no DSP scope change, no live Serato Database V2 writes.
- Every change is pure in-memory filtering, ordering, or warning construction.
