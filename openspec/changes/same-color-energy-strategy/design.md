# Design: Same Color & Energy Strategy

## Decision question

How do we enforce anchor color AND a ±1 energy band as combined hard
constraints for a single new strategy, reusing the two generic mechanisms
already in place, without changing `same_color` or `same_energy` by a single
byte?

## Architecture approach

Purely additive composition inside the existing recommendation pipeline. No
new filter logic is written: the change registers one profile and widens one
dispatch seam so the two hard filters that already exist run together for the
new strategy. The pipeline order in `recommend_playlist` is unchanged, so the
new strategy inherits color-then-energy composition, control-path preservation,
and the color fallback for free.

```text
BuildScreen combo  (auto-populated by list_strategy_catalog())
    │ recommend_requested("same_color_energy", ...)
    ▼
recommend_playlist(tracks, "same_color_energy", controls)
    │ _apply_strategy_filters        (no energy_range/bpm_range → no-op)
    │ _apply_genre_filter            (name != same_genre → skipped)
    │ _apply_color_filter            (name ∈ _COLOR_FILTER_STRATEGIES → RUNS)   ← widened seam
    │ apply_controls
    │ _apply_energy_tolerance        (energy_tolerance=1 is not None → RUNS)    ← data-driven, no seam change
    ▼
PlaylistRecommendation  (color-cohesive, ±1 energy, strategy-aware warnings)
```

The seam is deliberately asymmetric and mirrors how the codebase already
models the two axes: energy tolerance is a first-class `PlaylistStrategy`
field (`energy_tolerance`), so it activates automatically on any profile that
sets it; color has no model field and is name-dispatched, so it needs the seam
widened once.

## ADR-style decisions

### D1 — Color dispatch seam: name-set frozenset

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Module-level `_COLOR_FILTER_STRATEGIES: frozenset[str]` in `playlist_service.py`; replace both `strategy.name == "same_color"` checks with `strategy.name in _COLOR_FILTER_STRATEGIES` | Additive; local to the service; a set is just the plural of the `== "same_genre"` name-equality already used two lines above; no model/schema change; trivial rollback | Adds one module constant | **Selected.** |
| B. New `PlaylistStrategy` boolean field (e.g. `applies_color_filter`) | Data-driven like `energy_tolerance` | Touches the frozen model schema; every existing entry implicitly defaults `False`; broader blast radius; heavier to reason about for a byte-identical guarantee | Rejected. |

Rationale: house style dispatches color and genre by name equality, not by a
model flag. A frozenset is the minimal, in-idiom generalization of the existing
`== "same_color"` check and keeps the change inside one file. `same_color`
remains in the set, so its behavior is provably preserved.

### D2 — ScoringWeights for `same_color_energy`

Final weights: `harmonic=0.25, bpm=0.15, energy=0.30, tags=0.10, spectral=0.20`
(the proposal starting point, adopted unchanged).

Verification of "sum consistently": every existing profile except `same_color`
leaves `spectral` at its `0.10` default and sums to **1.10**; `same_color` is
the only profile that explicitly sets `spectral` (0.20) and sums to exactly
**1.00**. Since `same_color_energy` is the color sibling and likewise sets
`spectral` explicitly, it is aligned to the `same_color` convention and sums to
**1.00** (0.25+0.15+0.30+0.10+0.20). Relative to `same_color` it raises
`energy` 0.20 → 0.30 (reflecting the added energy intent) and lowers `harmonic`
0.30 → 0.25 and `bpm` 0.20 → 0.15 to fund it, while retaining `spectral=0.20`
for color cohesion. Weights are relative, not normalized; the validator only
requires non-negative components with a positive sum, so 1.00 is valid and
convention-consistent.

### D3 — Strategy-aware warning text (byte-identical for existing strategies)

Thread the active strategy name into the two name-hardcoded warning producers
and interpolate it. Interpolating `strategy.name` yields byte-identical text
for the existing strategies while naming `same_color_energy` for the new one.

- `_apply_energy_tolerance` already receives `strategy`. Change the line-512
  literal `"...outside same_energy energy tolerance"` to interpolate
  `strategy.name`. For `same_energy` → identical bytes; for `same_color_energy`
  → "...outside same_color_energy energy tolerance".
- `_apply_color_filter` does **not** receive the strategy today. Add a
  `strategy_name: str` parameter and interpolate it in both message lines (413
  "filter applied" and 418 "no candidates match anchor color ... falling back").
  Both call sites (`recommend_playlist` and `prefilter_strategy_candidates`)
  pass `strategy.name`. For `same_color` → identical bytes; for
  `same_color_energy` → strategy-named text.

Rejected alternative: keep the literals hardcoded and branch on strategy inside
the helpers — more code, and it would still hardcode `same_color`, which the
spec forbids the new strategy from emitting.

### D4 — Filter composition order and fallback precedence

Order is the **existing pipeline order, reused unchanged**: color filter runs
first (pre-`apply_controls`, lines 162–166), energy tolerance second
(post-`apply_controls`, lines 170–183). No reordering.

Fallback precedence:
- **Color empties the pool** → `_apply_color_filter` returns the original
  unfiltered `tracks` plus a `same_color_energy`-attributed fallback warning
  (existing color-fallback path, D3-renamed). Energy tolerance then runs on the
  restored pool. This is the single "fall back to unfiltered scoring" path the
  spec references, and it is the one the empty-pool test must exercise (build
  the case via a color mismatch).
- **Energy empties the pool after color succeeded** → identical to
  `same_energy` today: `_apply_energy_tolerance` filters and warns on the
  removed count with **no** fallback-to-unfiltered. We deliberately do **not**
  add a new energy fallback (additive-only; reuse existing paths). Precedence:
  color fallback takes effect first and can restore the pool; energy narrowing
  is terminal and matches existing `same_energy` semantics.

### D5 — StrategyName Literal extension and typing

Add `"same_color_energy"` to the `StrategyName` Literal in `strategies.py`.
This makes the new key valid for `_STRATEGIES: dict[StrategyName, ...]` and for
`available_strategies() -> list[StrategyName]`. Dispatch is `if`/`str`-based
(no `match`/exhaustiveness construct), and `_COLOR_FILTER_STRATEGIES` is typed
`frozenset[str]`, so there is no exhaustiveness break. pyright stays clean once
the Literal member and the dict entry land in the same change.

### D6 — Test plan skeleton (strict TDD, RED first)

Each item is a failing test authored before production code.

1. **Registration/enumeration** — assert `same_color_energy` appears in
   `available_strategies()` and `list_strategy_catalog()` with display label
   "Same Color & Energy"; assert `get_strategy("same_color_energy")` resolves
   and carries `energy_tolerance=1` and the D2 weights.
2. **Hard color enforcement** — anchor with a dominant color; assert every
   non-control candidate shares it.
3. **Hard energy enforcement** — anchor with an energy value; assert every
   non-control candidate is within ±1.
4. **Composition (both simultaneously)** — mixed pool; assert survivors satisfy
   color AND ±1 energy together, proving composition not substitution.
5. **Composition order / control-path preservation** — locked, start, end, and
   manual-prefix control tracks survive both filters in their positions even
   when they violate color or energy.
6. **Empty-pool fallback + warning attribution** — construct a color-mismatch
   pool so the color filter empties; assert fallback-to-unfiltered and a
   warning naming `same_color_energy`.
7. **Regression: byte-identical existing behavior** — snapshot `same_color` and
   `same_energy` ordered output and warnings on a fixed pool/anchor before and
   after; assert equality (guards the widened seam and the D3 interpolation).

## Affected files

- `src/xfinaudio/recommendation/strategies.py` — add `same_color_energy` to the
  `StrategyName` Literal; add the `_STRATEGIES["same_color_energy"]` entry
  (D2 weights, `energy_tolerance=1`).
- `src/xfinaudio/recommendation/playlist_service.py` — add
  `_COLOR_FILTER_STRATEGIES` frozenset; widen the two `strategy.name ==
  "same_color"` checks (`:162`, `:392`) to membership; add `strategy_name`
  param to `_apply_color_filter` and interpolate it (both call sites pass it);
  interpolate `strategy.name` in the `_apply_energy_tolerance` warning.
- `tests/test_playlist_strategies.py` — registration/enumeration/typing RED
  tests (D6.1).
- `tests/test_playlist_service.py` — color/energy/composition/control/fallback
  and byte-identical regression RED tests (D6.2–D6.7).

No desktop, scoring-engine, spectral-analyzer, or model-schema files change.

## Data model changes

None. `PlaylistStrategy` and `ScoringWeights` schemas are unchanged; only a new
frozen `_STRATEGIES` instance and one `StrategyName` Literal member are added.

## Safety

- No audio mutation; no DSP scope expansion; read-only spectral features only.
- No live Serato Database V2 writes.
- No new dependencies.
- `AppState` untouched.
- Purely additive and name-scoped: rollback is removing the Literal member, the
  `_STRATEGIES` entry, and reverting the seam/warning edits.
- Fits the 400-line review budget as one slice.
