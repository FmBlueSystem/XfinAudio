# Proposal: Carry the Bound Colour Anchor Through Prep Copilot Variant Planning

## Intent

`resolve-color-review-findings` (PR #339) made the main desktop recommendation route
bind a colour anchor once and carry it into final enforcement. Prep Copilot did not
follow: `PrepCopilotController.generate` took the plain records route for **every**
strategy, so each of the three variants re-resolved its own anchor from its own filtered
track list. A genre-focused variant could gate a DJ's set against a different colour than
the pool was planned for.

Authored retroactively — see `design.md` → "Process".

## Scope

### In scope

- G1: `PrepCopilotController.generate` routes colour strategies through
  `_desktop_color_anchor_candidate_context`, matching the main desktop route.
- G2: the strategy combo's value is normalised to an internal strategy name before the
  colour test. `currentData()` is empty for combos populated without user data, so the
  caller falls back to the display label ("Same Color") — which is not an internal
  strategy name, so the membership test silently missed and planned the set unanchored.
- G3: `color_anchor_path` threaded through `generate_prep_copilot_plan` →
  `build_prep_copilot_plan` → `_build_variant` → `recommend_playlist`, so every variant
  gates against the same bound track. A variant whose filter removes that track fails
  closed instead of rebinding a different anchor.
- G4: the two plan-builder seams retyped from `Callable[..., Any]` to `Protocol`s that
  spell the keyword contract, so an injected builder that cannot accept the anchor is a
  type error at the seam instead of a `TypeError` at generation time.

### Out of scope

- The bounded colour gate itself and the anchor-binding chain below Prep Copilot —
  shipped and verified by `resolve-color-review-findings`.
- `PrepCopilotController`'s remaining reaches into `MainWindow` privates through
  `_state`. Filed as a follow-up.

## Success criteria

1. Both colour strategies reach the plan chain through the anchor-bound context route;
   the plain records route is not called for them.
2. A combo yielding only a display label still reaches the colour route.
3. Every variant receives the same bound `color_anchor_path`; a variant that filters the
   anchor away returns an empty recommendation with a warning, not a re-anchored set.
4. `color_anchor_path=None` keeps flowing through the real chain so `recommend_playlist`
   resolves an anchor itself — the non-colour route and the unbound-anchor fallback.
5. All verification commands pass; version bumped and `uv.lock` synced.

## Rollback plan

The controller branch, the label normalisation, and the anchor threading are separable;
revert per item if a regression surfaces.

## Review budget

~105 production + ~320 test changed lines, within the 400-line budget.
