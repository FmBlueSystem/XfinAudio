# Specification: Recommendation Quality Harness and Pool-Collapse Fix

## Requirements

### R1. Read-only library loading

**GIVEN** an application-owned track database path
**WHEN** the evaluation harness loads tracks
**THEN** it reads via `TrackRepository.list_tracks()` only
**AND** it never writes to the database, the audio files, or any Serato file.

### R2. Deterministic anchor sampling

**GIVEN** a library of complete tracks and an integer seed
**WHEN** the harness samples N anchor tracks
**THEN** the same seed and library yield the same anchor set on every run.

### R3. Fill-rate metric

**GIVEN** an anchor and a strategy
**WHEN** the harness builds the candidate pool with the desktop candidate limit and runs
`recommend_playlist`
**THEN** it records `fill_rate = len(ordered_tracks) / requested_size`
**AND** the per-strategy report includes the mean fill rate and the count of runs that collapsed
to fewer than 3 tracks.

### R4. Hard-rule transition validity metric

**GIVEN** the ordered tracks of a recommendation
**WHEN** the harness evaluates each adjacent pair
**THEN** a pair is valid only if both Camelot keys are wheel-adjacent (same key, ±1 number on the
same letter, or relative major/minor) AND the BPM difference is ≤ 3%
**AND** the metric is the fraction of adjacent pairs that are valid
**AND** the validity rule is implemented inside the harness, independent of the scorer and of
`build_recommendation_pool` (the code under tuning).

### R5. Energy-curve monotonicity metric

**GIVEN** a directional strategy whose `prefer_energy_direction` is `ascending` (warmup, build)
**WHEN** the harness evaluates adjacent energy levels
**THEN** the metric is the fraction of adjacent pairs whose energy level is non-decreasing
**AND** for non-directional strategies the metric is reported as not-applicable.

### R6. Baseline report artifact

**GIVEN** a completed harness run
**WHEN** it finishes
**THEN** it emits a deterministic, human-readable report (per strategy: mean fill rate, collapse
count, mean transition validity, mean energy monotonicity, sample size)
**AND** the report is reproducible for a fixed seed and library snapshot.

### R7. Pool-collapse fix (PR2)

**GIVEN** an anchor whose best BPM/key-feasible candidates lack shared vibe tags
**WHEN** `build_recommendation_pool` selects the pool
**THEN** BPM/key feasibility is not starved by the tag-overlap partition, so feasible candidates
reach the pool
**AND** measured mean fill rate for affected strategies increases versus the recorded baseline
**AND** mean hard-rule transition validity does not regress versus the baseline.

## Non-functional

- The harness is offline and read-only; it must not mutate audio, the library DB, or Serato data.
- No DSP, beat tracking, or waveform analysis is added.
- Existing recommendation and presenter tests must keep passing.
- Each delivered slice stays within the 400-line review budget.
- All behavior changes follow strict TDD (failing test first).
