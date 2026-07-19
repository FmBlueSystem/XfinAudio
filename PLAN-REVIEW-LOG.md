# Plan Review Log: Removed playlist tracks must not be exported
No Act 1/2 grill — root cause was diagnosed directly by Claude (spec in PLAN.md), build delegated to Codex via /codex-build.
Builder model: gpt-5.6-sol (config default) — codex-cli 0.144.6. MAX_FIX_ROUNDS=2.

## Act 3 — Build

### Round 1 — Codex build
Implemented the frozen spec: new pure `recommendation_without_paths` helper in
`playlist_service.py` (filters `ordered_tracks`, recomputes `transition_scores`
for the new adjacencies via `_score_ordered_tracks`, updates `total_score`,
returns the original object untouched when nothing matches), applied at all 5
export read sites (3 in `serato_recommendation_export.py`, 2 in
`software_export_coordinator.py`), `playlist_removed_paths` added to the
`ExportHost` protocol, fake hosts updated. RED-first regression test
`test_serato_export_plan_excludes_track_removed_in_review` shown failing
pre-fix (`('kept.flac', 'removed.flac') != ('kept.flac',)`). Proof: 1066
passed, pyright 0, ruff clean, full release gate PASS.

### Claude's verdict — Round 1
- Verified the real-host wiring independently: `playlist_removed_paths` was
  already in `shell_state_compat.py:23`'s legacy attribute set, so the real
  MainWindow exposes it through the same compat layer `last_recommendation`
  already used — the fix works in production, not just against test fakes.
- Ran the proof myself: 1066 passed, pyright 0 errors, ruff clean.
- **One fidelity problem found**: the helper recomputed scores with
  `TransitionScoringConfig(weights=strategy.weights)` only, but the desktop
  generates recommendations WITH spectral cohesion from the Build screen
  slider (`recommendation_service.py:154`). After a removal, every recomputed
  export score would silently drop the spectral component — diverging from
  what the Review screen showed even for untouched adjacencies. → fix round.

### Round 2 — Codex fix (same session)
Added keyword-only `spectral_cohesion: float = 0.0` to
`recommendation_without_paths`, threaded into `TransitionScoringConfig`; all 5
call sites now pass `host.settings.scoring.spectral_cohesion` (kept in sync
with the Build slider by `settings_controller.py:44-47`); fake hosts gained a
`scoring` settings namespace. RED-first proof shown (TypeError for the
then-nonexistent kwarg), new test
`test_recommendation_without_paths_preserves_spectral_cohesion_for_new_seam`
asserts the parameter actually reaches the scoring.

### Claude's verdict — Round 2
Read the diff: all 5 call sites correct, helper signature correct. Ran the
full verification sequence myself: 1067 passed, pyright 0 errors, coverage
90.44% (gate 70%), ruff check/format clean, full release gate PASS. Known
residual edge (accepted): if the user moves the spectral-cohesion slider
after generating and before exporting without regenerating, the recomputed
scores use the new slider value — strictly more faithful than dropping the
component entirely, and the pre-existing generate/export split already has
this property. Build accepted; awaiting human diff sign-off.
