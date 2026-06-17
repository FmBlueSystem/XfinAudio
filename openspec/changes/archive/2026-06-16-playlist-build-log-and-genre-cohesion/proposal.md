# Proposal: Playlist Build Log + Genre Cohesion

## Intent
DJs report that generated playlists mix too many genres, and there is no way to see WHY a
playlist was built the way it was. Two linked problems:

1. **Genre barely influences construction.** In the default `harmonic_journey` strategy genre is
   folded into the `tags` component at weight 0.05 vs harmonic 0.60 (`strategies.py:48`), so genre
   can move a transition score by at most ~5% and is dominated 12:1 by harmonic compatibility.
2. **Genre matching is broken for multi-genre fields.** `_normalized_tags` (`scoring.py:289-293`)
   appends `track.genre` as one un-split string, so `"House, Disco"` and `"House, Funk"` register
   zero overlap even though both are House. The 0.05 weight therefore often contributes nothing.
3. **No build provenance.** There is zero logging in `recommend_playlist` and no structured record
   of which stages ran, how many candidates each filter dropped, or the per-transition genre
   relationship. Provenance only exists as flat `warnings` strings.
4. **"Genre focus" UI input is inert for normal recommend.** It is wired only to Prep Copilot
   (`prep_copilot.py:108-127`) with case-sensitive `==`, so it never affects `Recommend Playlist`.

## Scope (in)
- **Unit 1 — genre token fix**: comma-split genre in `_normalized_tags` so same-family tracks share
  tokens (mirror the existing `_genre_tokens` splitter already used by the `same_genre` filter).
- **Unit 2 — genre cohesion**: a configurable genre-cohesion control (0..1) that adds a soft
  same-genre reward / cross-genre penalty to transition scoring, plus wiring the existing
  "Genre focus" field into the normal `recommend_playlist` pool/score path (token-based, casefold).
- **Unit 3 — build log**: a structured, deterministic `PlaylistBuildLog` capturing pool size,
  each filter stage and its drop count, optimizer used, and a per-transition genre relation
  (same/adjacent/cross). Surfaced read-only in the UI and persisted via the existing JSON writer.

## Out of scope
- No audio mutation, no DSP, no live Serato DB writes (unchanged boundaries).
- No change to the Camelot/BPM/energy scoring math beyond the additive genre cohesion term.
- No ML/genre inference — genre comes only from existing metadata.

## Success criteria
1. Two tracks tagged `"House, Disco"` and `"House, Funk"` score a non-zero genre overlap (Unit 1).
2. With genre cohesion > 0, the eval harness shows measurably fewer cross-genre transitions on the
   real library vs cohesion 0, without breaking fill rate or hard-rule validity (Unit 2).
3. Every recommendation produces a `PlaylistBuildLog` whose stage drop counts reconcile with the
   final track count, visible in the UI and present in exported playlist JSON (Unit 3).
4. All verification commands pass; each unit stays within the 400-line review budget.

## Rollback
Each unit is independent. Revert order: Unit 3 (log) → Unit 2 (cohesion) → Unit 1 (token fix).
Genre cohesion defaults to 0 (current behavior) so Unit 2 is inert unless explicitly enabled.

## Delivery
Chained PRs, one per unit, `stacked-to-main`. Unit 1 first (smallest, clearest, measurable).
