# HELP-5 Scoring and Sequence Optimizer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add XfinAudio's first deterministic recommendation core: Camelot/BPM/energy/tag transition scoring plus small/large playlist sequence optimization.

**Architecture:** Keep algorithms in pure Python modules under `src/xfinaudio/recommendation/` with no UI, persistence, mutagen, DSP, or audio writes. Use `TrackRecord` as input. Return transparent scores/explanations so later UI/export stages can show why transitions were chosen.

**Tech Stack:** Python 3.11+, pydantic, pytest, ruff, uv.

---

## Non-goals

- No DSP, key detection, BPM detection, beat tracking, audio rendering, or audio mutation.
- No PySide6 UI changes unless needed to expose existing scanned records later.
- No exports.
- No Serato work.

## Task 1: Camelot compatibility scoring

**Files:**
- Create: `src/xfinaudio/recommendation/__init__.py`
- Create: `src/xfinaudio/recommendation/camelot.py`
- Test: `tests/test_camelot_scoring.py`

**Steps:**
1. Write failing tests for exact same key, adjacent wheel move, relative A/B move, diagonal fuzzy moves, controlled energy boost rule, incompatible key, and invalid key.
2. Run: `uv run pytest -v tests/test_camelot_scoring.py` and confirm RED.
3. Implement `CamelotKey`, `parse_camelot_key`, and `score_camelot_transition(from_key, to_key, boost_rules=None)`.
4. Use deterministic scores: same `1.0`, adjacent same-letter `0.9`, relative same-number A/B `0.85`, diagonal fuzzy `0.7`, configured boost `0.8`, incompatible `0.0`.
5. Run focused test and full suite.

## Task 2: Feature transition scoring

**Files:**
- Create: `src/xfinaudio/recommendation/scoring.py`
- Test: `tests/test_transition_scoring.py`

**Steps:**
1. Write failing tests for BPM compatibility, energy compatibility, tag overlap, missing optional tags, incomplete required metadata, and weighted final score.
2. Run focused test and confirm RED.
3. Implement pydantic `ScoringWeights`, `TransitionScore`, and `score_transition(left, right, weights=...)`.
4. Default weights: harmonic `0.40`, bpm `0.25`, energy `0.25`, tags `0.10`; validate total > 0 and redistribute when tag score unavailable.
5. Ensure explanations include component scores and warnings for missing required metadata.
6. Run focused test and full suite.

## Task 3: Sequence optimizer

**Files:**
- Create: `src/xfinaudio/recommendation/optimizer.py`
- Test: `tests/test_sequence_optimizer.py`

**Steps:**
1. Write failing tests for exact optimizer choosing best ordering for <=20 tracks, respecting start/end constraints when provided, and deterministic greedy+2-opt behavior for >20 tracks.
2. Run focused test and confirm RED.
3. Implement `recommend_sequence(tracks, start_path=None, end_path=None, exact_limit=20)`.
4. Use Held-Karp dynamic programming for <=20 unconstrained/small enough cases; use greedy initialization + 2-opt for >20.
5. Return ordered `TrackRecord` list plus transition scores/explanations.
6. Run focused test and full suite.

## Task 4: Documentation and verification

**Files:**
- Create: `docs/help-5-scoring-sequence-optimizer.md`

**Steps:**
1. Document scoring defaults, exact/heuristic optimizer behavior, non-goals, and limitations.
2. Run:
   - `uv run pytest -v`
   - `uv run ruff check .`
   - `uv run ruff format --check .`
3. Run fresh review before accepting HELP-5.
4. Update Jira HELP-5 with evidence and transition to done only after review has no blockers.
