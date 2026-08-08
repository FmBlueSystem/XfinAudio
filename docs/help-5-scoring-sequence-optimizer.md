# HELP-5 Scoring and Sequence Optimizer

HELP-5 adds the first deterministic recommendation core for XfinAudio. It uses scanned `TrackRecord` metadata plus persisted, read-only audio profiles; it does not mutate, render, mix, or export audio.

## Camelot scoring

`xfinaudio.recommendation.camelot` parses Camelot keys from `1A` through `12B` and scores harmonic moves with fixed values:

- same key: `1.0`
- adjacent same-letter wheel move: `0.9`
- relative same-number A/B move: `0.85`
- diagonal fuzzy move: `0.7`
- configured boost rule: `0.8`
- incompatible move: `0.0`

Configured boosts are passed as a collection of `(from_key, to_key)` tuples. Keys are normalized case-insensitively before matching.

## Transition scoring

`xfinaudio.recommendation.scoring.score_transition(left, right, boost_rules=None)` returns a `TransitionScore` with component scores, warnings, and explanations. Controlled boost rules are passed through to harmonic scoring. Default weights are:

- harmonic: `0.40`
- BPM: `0.25`
- energy: `0.25`
- tags: `0.10`
- spectral: `0.10`
- danceability: `0.0` (opt-in)

BPM scoring compares percentage difference using the lower BPM as the denominator:

- `<= 2%`: `1.0`
- `<= 4%`: `0.75`
- `<= 8%`: `0.5`
- otherwise: `0.0`

Energy scoring compares absolute energy difference:

- `<= 1`: `1.0`
- `<= 2`: `0.7`
- `<= 3`: `0.4`
- otherwise: `0.0`

When cue-derived boundary values exist on both sides, energy compares `energy_out(A)` with `energy_in(B)`: the sections that actually touch during a mix. If either boundary value is absent, scoring falls back to the whole-track `energy_level` scalars.

Tag scoring uses normalized Jaccard overlap across `tags` plus `genre`. An unavailable component scores the neutral `NEUTRAL_COMPONENT_SCORE = 0.5` and stays in the denominator. Its weight is not redistributed: redistribution inflated totals for poorly described tracks, so the optimizer systematically preferred the least-documented material. Neutral scoring preserves the intended ordering: clash < unknown < match.

Danceability is measured from the audio as pulse clarity × tempo confidence × a percussive gate. Its default weight is `0.0`, so it is opt-in; `peak_time` and `same_energy` enable it at `0.10`. If either track has no danceability profile, the component is neutral, never a penalty.

Mixed In Key beatgrid onsets also correct a known half-time tempo case. With at least 16 strictly ascending onsets that imply double the declared `tempo`, the measured grid wins; malformed grids fall back to the declared tempo. BPM comparisons fold 2:1 pairs consistently across the scorer, optimizer gate, quality report, candidate pool, and live assistant.

Every successful transition also exposes two informative axes:

- `compatibility_score`: harmonic, tags, danceability, and spectral — do these tracks belong in the same set?
- `mixability_score`: BPM and energy handoff — can these tracks be joined?

These axes explain the transition; they do not replace or alter `total_score`. The optimizer still maximizes `total_score`.

Required recommendation metadata is `camelot_key`, `bpm`, and `energy_level`. If either track lacks required metadata or carries an invalid Camelot key, the transition returns `0.0` with warnings. Scoring weights must be non-negative and at least one component must be enabled.

## Sequence optimizer

`xfinaudio.recommendation.optimizer.recommend_sequence(tracks, start_path=None, end_path=None, exact_limit=20, boost_rules=None)` returns a `SequenceRecommendation` containing ordered tracks, transition scores, total score, and optimizer name. Controlled boost rules are used both in pairwise scoring and final transition explanations.

For playlists at or below `exact_limit`, the optimizer uses Held-Karp dynamic programming to maximize the sum of adjacent transition scores. Optional start and end paths constrain the first and last tracks. The implementation stores scores plus predecessor pointers rather than complete path tuples per DP state.

For larger playlists, the optimizer uses deterministic greedy initialization followed by 2-opt local improvement. Ties are resolved by track path so repeated runs return the same order.

## Non-goals and limitations

- No key detection, general BPM detection, rendering, mixing, exports, Serato integration, or UI surfacing of the informative axes.
- Scores are only as reliable as the scanned metadata and persisted audio profiles.
- The heuristic optimizer for playlists above `exact_limit` is deterministic but not guaranteed globally optimal.
- Exact optimization has exponential memory/time growth and should stay limited to small playlists. Local probe on this machine: 20 complete tracks routed through exact optimization in about 36 seconds, so future UI work should run exact optimization in a background worker with progress/cancel or lower `exact_limit` for interactive use.

## Future: intro/outro spectral profiles

This is not implemented. A future pass could locate opening and closing windows with the first and last cue points, analyze them, persist them like the existing profile, and feed the mixability axis by comparing `outro(A)` with `intro(B)` — the same shape as the energy handoff.

Today there is one spectral profile per track, measured from a 30-second window at the track's MIDDLE: the one region a DJ never mixes through.
