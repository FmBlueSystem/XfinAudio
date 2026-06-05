# HELP-5 Scoring and Sequence Optimizer

HELP-5 adds the first deterministic recommendation core for XfinAudio. It uses scanned `TrackRecord` metadata only; it does not inspect, mutate, render, mix, export, or analyze audio.

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

BPM scoring compares percentage difference using the lower BPM as the denominator:

- `<= 2%`: `1.0`
- `<= 4%`: `0.75`
- `<= 8%`: `0.5`
- otherwise: `0.0`

Energy scoring compares absolute `energy_level` difference:

- `<= 1`: `1.0`
- `<= 2`: `0.7`
- `<= 3`: `0.4`
- otherwise: `0.0`

Tag scoring uses normalized Jaccard overlap across `tags` plus `genre`. If both tracks lack tags and genre, tag scoring is unavailable and its weight is redistributed over the available components.

Required recommendation metadata is `camelot_key`, `bpm`, and `energy_level`. If either track lacks required metadata or carries an invalid Camelot key, the transition returns `0.0` with warnings. Scoring weights must be non-negative and at least one component must be enabled.

## Sequence optimizer

`xfinaudio.recommendation.optimizer.recommend_sequence(tracks, start_path=None, end_path=None, exact_limit=20, boost_rules=None)` returns a `SequenceRecommendation` containing ordered tracks, transition scores, total score, and optimizer name. Controlled boost rules are used both in pairwise scoring and final transition explanations.

For playlists at or below `exact_limit`, the optimizer uses Held-Karp dynamic programming to maximize the sum of adjacent transition scores. Optional start and end paths constrain the first and last tracks. The implementation stores scores plus predecessor pointers rather than complete path tuples per DP state.

For larger playlists, the optimizer uses deterministic greedy initialization followed by 2-opt local improvement. Ties are resolved by track path so repeated runs return the same order.

## Non-goals and limitations

- No DSP, key detection, BPM detection, beat tracking, rendering, mixing, exports, Serato integration, or UI work.
- Scores are metadata-driven and only as reliable as the scanned metadata.
- The heuristic optimizer for playlists above `exact_limit` is deterministic but not guaranteed globally optimal.
- Exact optimization has exponential memory/time growth and should stay limited to small playlists. Local probe on this machine: 20 complete tracks routed through exact optimization in about 36 seconds, so future UI work should run exact optimization in a background worker with progress/cancel or lower `exact_limit` for interactive use.
