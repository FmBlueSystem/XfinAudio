# Proposal: Resolve Two-Axis Review Findings for Colour Strategies

## Intent

Close the findings a two-axis review (Standards + Spec) raised against the bounded
colour gate shipped by `tighten-spectral-color-filters` (PRs #336, #337). Three are
correctness bugs in anchor binding and pool trimming; the rest are lost warnings,
a duplicated filter pair, and a private cross-package import.

Authored retroactively — see `design.md` → "Process".

## Scope

### In scope

- F1: `_resolve_color_anchor`'s first-profiled fallback could bind a **locked** track as
  the colour anchor. The candidate pool puts every control at the front, so an
  unfiltered scan picked a locked track whenever no start/manual control named one.
- F2: `same_color` re-resolved its anchor from the reshaped pool. The gate runs once in
  the prefilter and again in `recommend_playlist`; re-resolving could bind a different
  anchor than the pool was narrowed for and empty a pool that had already passed.
- F3: `build_recommendation_pool` displaced whatever sat in the last slot to retain the
  protected anchor — including a control, which `apply_controls` then rejects downstream.
- F4: the colour-prerequisite warning was emitted conditionally, so a DJ could get an
  empty result with no explanation of why the pool stayed strict.
- F5: the informational `"{strategy} filter applied: {color}"` warning was lost during
  the `tighten-*` rewrite.
- F6: `same_color` and `same_color_energy` carried two near-copies of the same filter,
  free to drift apart.
- F7: `desktop/main_window.py` reached into a private symbol of another package.
- F8: dishonest naming and unguarded float math — `_mixed_profile_close` no longer
  handled only MIXED, and non-finite spectral features were not rejected.

### Out of scope

- The bounded gate's thresholds and predicates (`COLOR_*` constants, energy matching) —
  unchanged from `tighten-spectral-color-filters`.
- Prep Copilot's variant chain: it still planned colour sets unanchored. Filed as a
  follow-up and shipped separately as `prep-copilot-color-anchor` (PR #340).

## Success criteria

1. A locked track is never selected as the colour anchor.
2. A colour anchor is bound once, before the pool is reshaped, and both gate passes use
   that exact identity. A supplied anchor path absent from the pool fails closed rather
   than silently re-resolving a different one.
3. Retaining the protected anchor never evicts a control.
4. The prerequisite warning is emitted whenever the prerequisite is missing.
5. The `"{strategy} filter applied: {color}"` informational warning is present again.
6. One filter implementation serves both colour strategies; one constant answers "does
   this strategy run the bounded colour gate?" at every dispatch site.
7. All verification commands pass; version bumped and `uv.lock` synced.

## Rollback plan

Each finding is an isolated function-level change with dedicated regression tests;
revert per-finding if a regression surfaces.

## Review budget

~180 production + ~290 test changed lines, within the 400-line budget.
