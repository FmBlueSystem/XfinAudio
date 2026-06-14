# Proposal: Genre-Stable Playlist Routing

## Intent

Stop the recommender from mixing unrelated genres (World & Latin next to Rock, House, Synth Pop) while preserving the existing strategy flexibility for DJs who want variety.

## Scope

### In scope

- Add a new playlist strategy that constrains candidates to the dominant genre of the user-selected anchor tracks.
- Reuse the existing same-color pattern so the new strategy is symmetric and discoverable.
- Add a "Same Genre" tooltip and a "Filter by genre" pre-scorer that the new strategy uses.
- Add tests proving genre stability across realistic candidate pools.

### Out of scope

- Changing genre parsing or metadata extraction.
- Penalizing genre change in all strategies (can be added later).
- Genre category vs specific genre disambiguation.
- Persisting the DJ's preferred genre beyond a recommendation run.

## Motivation

Manual QA showed a 23-track recommendation jumping from World & Latin to Rock to Synth Pop to House within 5 transitions, because key/BPM/energy were favorable (5A/5B, energy 6) but genre was ignored. The DJ needs a strategy that guarantees genre coherence without sacrificing harmonic compatibility.

## Arbor analysis

We treat the problem as a hypothesis tree and refine toward the best route.

### Hypothesis branches

| Branch | Route | Impact | Risk | Cost | UX |
|---|---|---|---|---|---|
| H1a | New "Same Genre" strategy | High (isolated) | Low (opt-in) | Low | High (discoverable in combo) |
| H1b | Reusable genre filter for any strategy | High | Medium (touches optimizer) | Medium | Medium |
| H1c | Genre category (group) instead of raw genre | Medium | Medium (needs new metadata) | High | High |
| H2a | Fixed penalty for genre change | Medium | Medium (affects all strategies) | Low | Low (hidden knob) |
| H2b | Penalty proportional to tag weight | Low | Low | Low | Low |
| H2c | Slider for "genre stability" | Medium | Medium (more UI) | Medium | High (user control) |
| H3a | Genre as pre-scorer filter (internal) | High | Low | Medium | Low (no user affordance) |
| H3c | Hard constraint in optimizer | High | Medium | High | Low |

### Refinement

- Eliminate H1c (no genre category data exists; out of scope).
- Eliminate H3c (too invasive, overlapping with H3a).
- Combine H1a and H3a: the new strategy uses a genre pre-scorer filter internally.
- Defer H2c to a follow-up if DJs ask for it.

### Best route: H1a + H3a

Add a `same_genre` strategy that:
1. Reads the genre of the selected anchor tracks.
2. Filters the candidate pool to tracks whose primary genre matches.
3. Reuses the same scoring/weighting as the other strategies.
4. If no tracks match, falls back to the same scoring without filter and surfaces a warning.

This mirrors `same_color` (spectral pre-scorer), is opt-in (no regression), and is symmetric with existing features.

## Success criteria

1. Selecting the "Same Genre" strategy with anchor tracks from "World & Latin" produces a recommendation where all tracks share that primary genre (or are flagged as fallback).
2. Other strategies are unchanged.
3. All verification commands pass.
4. No audio files are mutated.

## Rollback plan

- Remove the `same_genre` strategy from the registry.

## Review budget

Estimated changed lines: ~120 production + ~60 test lines, within the 400-line budget.
