# dj-recommendation-safety Specification

## Purpose

Define correctness and safety contracts for the recommendation engine's transition scoring cache, BPM pre-filtering, optimizer exact-solver threshold, background-thread lifecycle guards, and CI test environment cleanliness.

## Requirements

### Requirement: Transition Score Session Cache

`score_transition(left, right, weights, config)` MUST return a cached result for identical `(left.path, right.path, weights, config)` inputs within the same recommendation session, and the cache MUST be cleared between sessions.

#### Scenario: Cache hit returns same value

- GIVEN a recommendation session is active
- WHEN `score_transition` is called twice with identical `(left.path, right.path, weights, config)` arguments
- THEN the second call MUST return the same value as the first
- AND the underlying scoring computation MUST run only once

#### Scenario: Cache is cleared between sessions

- GIVEN a recommendation session ends and a new one begins
- WHEN `score_transition` is called with the same arguments as a previous session
- THEN the cache MUST NOT return the stale value from the previous session
- AND the scoring computation MUST run fresh

#### Scenario: Existing scoring tests pass

- GIVEN the full scoring test suite
- WHEN run after cache is added
- THEN all existing tests MUST pass without modification

### Requirement: BPM Pre-filter Before Optimizer

BPM-jump candidates MUST be excluded from the candidate pool BEFORE the TSP optimizer is invoked; post-optimizer BPM drop logic MUST be removed.

#### Scenario: Optimizer never receives BPM-violating candidates

- GIVEN a candidate pool containing tracks with BPM jumps that exceed the configured threshold
- WHEN `build_playlist` is called
- THEN the optimizer MUST receive only candidates that pass the BPM filter
- AND no BPM-violating candidate MUST appear in the optimizer's input

#### Scenario: Post-optimizer BPM drop is absent

- GIVEN the playlist service executes a full recommendation
- WHEN the optimizer returns its ordered result
- THEN no BPM-jump filtering step MUST occur after the optimizer call

#### Scenario: Playlist output remains deterministic

- GIVEN fixed input tracks, weights, and config
- WHEN `build_playlist` is called twice with the same inputs
- THEN both calls MUST return the same ordered playlist

### Requirement: Exact Solver Cap at n≤15

The exact TSP solver MUST only run when the candidate pool contains 15 or fewer tracks; pools of 16 to 25 tracks MUST use the heuristic path.

#### Scenario: Exact solver runs for n=15

- GIVEN a candidate pool of exactly 15 tracks
- WHEN the optimizer is invoked
- THEN the exact TSP solver MUST be used
- AND the constant `EXACT_LIMIT` MUST equal `15`

#### Scenario: Heuristic runs for n=16

- GIVEN a candidate pool of exactly 16 tracks
- WHEN the optimizer is invoked
- THEN the heuristic path MUST be used
- AND the exact TSP solver MUST NOT be invoked

#### Scenario: Heuristic runs for n=25

- GIVEN a candidate pool of exactly 25 tracks
- WHEN the optimizer is invoked
- THEN the heuristic path MUST be used

### Requirement: Background Thread Lifecycle Guards

Starting a new scan or recommendation while one is already running MUST cancel the previous operation and wait for it to stop before starting the new one; stale thread results MUST NOT update the UI.

#### Scenario: New scan cancels previous scan

- GIVEN a scan is in progress
- WHEN the user starts a new scan
- THEN the previous scan thread MUST be cancelled
- AND the controller MUST wait for the previous thread to stop before starting the new one

#### Scenario: New recommendation cancels previous recommendation

- GIVEN a recommendation is in progress
- WHEN the user requests a new recommendation
- THEN the previous recommendation thread MUST be cancelled
- AND the controller MUST wait for it to stop before starting the new one

#### Scenario: Stale thread result is ignored

- GIVEN a scan or recommendation thread is cancelled and a new one starts
- WHEN the cancelled (stale) thread eventually emits a completion signal
- THEN the UI MUST NOT be updated with the stale result

#### Scenario: closeEvent uses public cancel API

- GIVEN a scan or recommendation is running
- WHEN the application window receives a close event
- THEN the controller MUST cancel the operation via its public cancel API
- AND the close handler MUST NOT access private thread attributes directly

### Requirement: CI Test Environment Cleanliness

Both `test_pyinstaller_packaging.py` and `test_release_gate_check.py` MUST pass in a clean checkout where `build/` and `dist/` are absent from the repo root; `build/` and `dist/` MUST be listed in `.gitignore`.

#### Scenario: Tests pass with no build artifacts present

- GIVEN a clean checkout with no `build/` or `dist/` directory
- WHEN `uv run pytest -q tests/test_pyinstaller_packaging.py tests/test_release_gate_check.py` is executed
- THEN both tests MUST pass with zero failures

#### Scenario: build/ and dist/ are gitignored

- GIVEN the repository `.gitignore`
- WHEN it is inspected
- THEN `build/` and `dist/` MUST each appear as ignored patterns
