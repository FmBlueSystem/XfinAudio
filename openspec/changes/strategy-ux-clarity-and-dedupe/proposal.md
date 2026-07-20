# Proposal: Strategy UX Clarity and Duplicate Dedupe

## Intent

Driving the real app end-to-end against the user's 10,392-track library
(2026-07-20 verification of `same_color_energy`) surfaced three UX defects the
user asked to fix together:

1. **Stale strategy description.** `strategy_explanation_label` only refreshes on
   render/state sync, never on combo change (the combo has no change-signal
   wiring). After switching to `same_color_energy`, the label kept showing
   `harmonic_journey`'s text until a tab switch forced a render. The previous
   change shipped guarantee-explicit descriptions that users still cannot see at
   selection time.
2. **Dropdown shows internal names.** The combo lists `same_color_energy`,
   `harmonic_journey` instead of `display_name` ("Same Color & Energy").
3. **Duplicate versions in recommendations.** The candidate pool does not dedupe
   near-duplicate versions — one 20-track playlist held "Too Hot" x2, "Se La" x2,
   "Still" x2. Library-side hiding already exists; the recommendation pool does not.

## Proposal Question Round

Interactive questions skipped: the three defects, their fixes, and constraints are
pre-decided with the user. Assumptions carried to spec/design:

- Dropdown switches to `display_name`; `StrategyRegistry.resolve_name` already
  accepts both, so downstream resolution keeps working. Persisted artifacts
  (export JSON `recommendation.strategy.name`) MUST stay internal names.
- Control paths (locked/start/end/manual) are NEVER deduped away; the anchor
  always survives.
- Output for libraries WITHOUT duplicates is unchanged; color/energy semantics
  untouched.

## Scope

### In Scope
- Refresh `strategy_explanation_label` immediately on strategy-combo change.
- Populate the combo with display names (internal name preserved as item data).
- Dedupe the recommendation candidate pool: one representative per duplicate
  group, controls always preserved.
- Audit every consumer of the emitted strategy string (recommendation service,
  `prefilter_strategy_candidates`, prep copilot, saved playlists, exports) to
  confirm display-name emission and internal-name persistence both hold.
- Strict-TDD coverage for all three items.

### Out of Scope
- Changing color/energy strategy semantics or scoring.
- Library-screen duplicate hiding (already shipped).
- Any new duplicate-detection heuristic beyond the existing grouping helpers.
- UI redesign; new strategies.

## Capabilities

### New Capabilities
- `strategy-selection-ux`: combo shows display names and the explanation label
  updates immediately on selection, stating actual guarantees.
- `recommendation-duplicate-version-dedupe`: recommendation candidate pool keeps
  one representative per duplicate-version group; control paths always survive;
  duplicate-free libraries are unchanged.

### Modified Capabilities
- None. Existing strategy filtering/scoring and library-hide behavior are
  preserved; changes are additive UX plus a pool-level dedupe seam.

## Approach

Follow RED → GREEN → REFACTOR → VERIFY.

1. **Item 1** — wire the strategy combo's change signal (currently absent) to a
   slot that sets `strategy_explanation_label` from `vm.strategy_explanation(...)`.
2. **Item 2** — add combo items as `(display_name, internal_name)`; keep
   `currentData()` as the internal key; `_on_recommend`/render resolve through
   `resolve_name`. Assert persisted strategy names stay internal.
3. **Item 3** — reuse the pure grouping helpers currently in
   `desktop/library_filter.py` (`_duplicate_group_key`,
   `_pick_duplicate_representative`, `suppressed_duplicate_paths`). Design decides
   where the shared pure helpers live so the recommendation layer does NOT import
   from `desktop`. Apply dedupe in the candidate pool with control paths preserved.

Natural PR split if the three items overflow 400 lines: UI items 1+2 vs pool item 3.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/screens/build_screen.py` | Modified | Combo change-signal wiring; display-name items; label refresh |
| `src/xfinaudio/desktop/library_filter.py` | Modified | Extract/relocate pure grouping helpers to a layer-safe module |
| `src/xfinaudio/recommendation/playlist_service.py` | Modified | Dedupe candidate pool preserving control paths |
| `tests/` | Modified | RED tests for label refresh, display names, pool dedupe, control survival |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Display-name combo breaks a downstream consumer | Medium | Full consumer audit; `resolve_name` handles both; persistence asserted internal |
| Recommendation layer imports from `desktop` | Medium | Relocate pure helpers to a shared layer-safe module in design |
| Dedupe removes a control/anchor track | Medium | Always preserve control paths; representative test on anchor survival |
| Dedupe changes output for duplicate-free libraries | Low | Assert unchanged output when no group has >1 member |
| Three items exceed 400-line budget | Medium | Forecast in tasks; split UI (1+2) vs pool (3) |

## Rollback Plan

Revert the change. All three items are additive: removing the combo signal wiring,
reverting combo items to internal names, and removing the pool dedupe call restore
prior behavior with no persisted-data impact.

## Dependencies

- Existing `uv`, pytest, Pyright, Ruff, release gate. No new runtime deps.

## Success Criteria

- [ ] Changing the strategy combo updates the explanation label immediately.
- [ ] The dropdown shows display names; emitted/persisted strategy names resolve
      correctly and stay internal in exports.
- [ ] Recommendation candidate pool contains one representative per duplicate
      group; control/anchor tracks always survive.
- [ ] Duplicate-free libraries produce identical output to today.
- [ ] Full verification and the release gate pass.
