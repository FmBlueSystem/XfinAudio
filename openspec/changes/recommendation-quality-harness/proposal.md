# Proposal: Recommendation Quality Harness and Pool-Collapse Fix

## Intent

Give XfinAudio an objective, scorer-independent way to **measure** playlist recommendation
quality across the real library, then use that instrument to **fix** the most damaging real
defect: recommended playlists collapse to 1–2 tracks because candidate-pool ranking and the
adjacent BPM-jump guard interact badly.

## Context and evidence

- Library DB (`~/.xfinaudio/xfinaudio.sqlite3`): **10,607 tracks**, metadata near-complete
  (10,570 complete; BPM/energy/Camelot ≈100%). Plenty of data to measure against.
- Saved playlists (`playlists.db`): **1,514 playlists, all of size 1 or 2** (866×1, 648×2);
  **zero** curated multi-track sets. There is **no external ground-truth corpus** of real DJ
  sequences to learn from or validate against.
- Prior validation (memory #2574, re-verified 2026-06-15 as #2873): of three reported
  recommendation defects, **two are already fixed** (`same_energy` energy-tolerance filter;
  candidate-pool sort key now gates BPM/key before tag overlap). The remaining real problem is
  the **playlist collapse to 1–2 tracks**, traceable to `build_recommendation_pool` still
  hard-partitioning tag-overlap candidates ahead of BPM-feasible ones, after which
  `_drop_generated_tracks_after_impossible_bpm_jumps` discards most of the pool.

## Why not run the Arbor runtime directly

`RUC-NLPIR/Arbor` optimizes a numeric metric against a held-out dev/test split. XfinAudio has
neither a quality metric nor a labeled split today. The only existing numeric signal is the
recommender's own `total_score`, and optimizing the system against its own scorer is circular.
We therefore apply **Arbor-style hypothesis-tree reasoning** (already the house convention in
this repo's proposals) and first **build the missing measurement instrument**. Running the Arbor
runtime becomes viable only after a trustworthy `run_eval` metric exists; that is explicitly a
follow-up, not this change.

## Scope

### In scope

- A **read-only evaluation harness** that samples N anchor tracks from the library, runs each
  strategy via the existing `recommend_playlist` API, and reports three scorer-independent
  metrics per strategy:
  1. **Fill rate** — final playlist length vs. requested size (exposes the 1–2 track collapse).
  2. **Hard-rule transition validity** — fraction of adjacent pairs passing Camelot wheel
     adjacency AND BPM jump ≤ 3%.
  3. **Energy-curve monotonicity** — for directional strategies (warmup/build), fraction of
     adjacent pairs respecting the intended energy direction.
- A baseline report committed as evidence.
- A **fix to the pool-collapse defect** in `build_recommendation_pool`, driven by RED tests and
  measured before/after with the harness.

### Out of scope

- Running the Arbor CLI runtime or installing `arbor`.
- Any DSP, audio mutation, or Serato V2 writes.
- Changing the scoring weights of any strategy (separate future change).
- Building a labeled ground-truth playlist corpus.
- UI changes.

## Arbor analysis

Hypothesis tree for "improve the algorithms with evidence".

| Branch | Route | Impact | Risk | Cost | Verdict |
|---|---|---|---|---|---|
| H1a | Build read-only metric harness, then fix guided by it | High | Low | Med | **Selected** |
| H1b | Fix pool collapse blind, no harness | Med | Med (no regression signal) | Low | Rejected — no proof of improvement |
| H2a | Metric = recommender's own `total_score` | Low | High (circular) | Low | Rejected — optimizes against itself |
| H2b | Metric = hard DJ rules (Camelot/BPM/energy) | High | Low | Med | **Selected** — scorer-independent |
| H2c | Metric = imitation of real saved playlists | — | — | — | Eliminated — no multi-track corpus exists |
| H3a | Run Arbor runtime now | Low | High | High | Deferred — needs H1a metric first |

**Best route: H1a + H2b**, with Arbor runtime (H3a) deferred until the harness is trusted.

## Success criteria

1. Harness runs offline against the real library and emits the three metrics per strategy
   without mutating any file.
2. Baseline report quantifies the current 1–2 track collapse.
3. After the pool-collapse fix, average fill rate for affected strategies improves measurably,
   with hard-rule transition validity not regressing.
4. All verification commands pass.
5. No audio mutation, no DSP, no Serato V2 writes.

## Rollback plan

- Harness is additive and read-only; remove the script/module to revert.
- The pool fix is isolated to `build_recommendation_pool`; revert that function to restore prior
  ranking.

## Review budget and chained PRs

Estimated total exceeds a single review comfortably, so deliver as **chained PRs**:

- **PR 1 — Harness** (`eval_recommendation` + metrics + tests + baseline report): ~200 prod + ~120 test lines.
- **PR 2 — Pool-collapse fix** (`build_recommendation_pool` + RED/GREEN tests + before/after numbers): ~80 prod + ~80 test lines.

Each slice stays within the 400-line review budget.
