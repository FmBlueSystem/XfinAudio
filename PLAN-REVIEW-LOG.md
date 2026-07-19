# Plan Review Log: Analyze mid-track window for spectral color (analyzer phase 2)

Act 1 (grill) complete — direction locked with the user after an 80-track empirical experiment
(power=2.0 rejected with data; mid-track window confirmed as the change worth a rescan). MAX_ROUNDS=5.
Reviewer model: gpt-5.6-sol (config default) — codex-cli 0.144.6.

## Round 1 — Codex (effort: high)

1. BUG — rescan never starts for stale profiles: `LibraryController.start_spectral_completion_worker` filters `spectral_profile is None` before the worker sees records.
2. BUG — a normal metadata scan erases preserved colors: with stale profiles excluded from the cache, `save_scan_results` overwrites `spectral_profile_json` with NULL.
3. BUG — version 2 does not uniquely mean "middle 30s": batch/sequential paths call `analyze_spectral_profile` with no duration cap (full track) while worker/scan use 30s.
4. RISK — rollout completion unprovable: failed analyses emit None but still finish; unqualified validation SQL would mix v1/v2 and drive a bad retune.
5. RISK — `< CURRENT` accepts future versions as current; freshness must be exact equality.

VERDICT: REVISE

### Claude's response

All five ACCEPTED after verification against source:
- #1 confirmed at library_controller.py:381-382 — controller gate added to the plan with regression test.
- #2 confirmed conceptually (upsert nulls profile when incoming record has none) — COALESCE-preservation added with scan-during-rescan test.
- #3 confirmed and worse than stated: batch_analyzer.py:29 and :128 already analyze the FULL track today while scan_service/worker use 30s — two windows coexist in production. Plan now mandates one canonical mid-window default inside analyze_spectral_profile with a cross-path test.
- #4 accepted — validation SQL filters analysis_version = 2; counts recorded; retune withheld until completion is proven.
- #5 accepted — freshness is exact equality at every gate.

## Round 2 — Codex (effort: high)

Addressed: controller gate, exact-equality versioning, rollout accounting. Remaining:
1. BUG — unconditional COALESCE poisons cache identity: changed file + preserved old profile + new mtime/size = obsolete profile looks current after interrupted rescan.
2. BUG — repository preservation does not stop the live UI from blanking: scan returns profile-less records and show_tracks renders them directly.
3. RISK — v2 can still mean a noncanonical window: LibrosaSpectralAnalyzer forwards None/arbitrary durations.

VERDICT: REVISE

### Claude's response

All three ACCEPTED:
- #1: preservation is now identity-guarded — keep stored profile only when stored mtime/size match the incoming file; changed file stores NULL. File-changed regression test added.
- #2: scan_folder now attaches identity-matched stored profiles (any version, display only) to returned records after saving; re-analysis queueing unaffected. Regression test added.
- #3: accepted and simplified further — the `max_duration_seconds` parameter is REMOVED from analyze_spectral_profile and the adapter entirely; the canonical mid-window is a module constant, making a noncanonical v2 stamp impossible by construction.

## Round 3 — Codex (effort: high)

Prior three addressed. One new:
1. BUG — two cache consumers bypass version freshness: analysis_planning.try_cached_profile and scan_service._lookup_previous_profile trust mtime/size alone, so caller-supplied caches can resurrect v1 profiles.

VERDICT: REVISE

### Claude's response

ACCEPTED — the exact-version predicate now applies at both consumption helpers too, with RED tests for identity-matched v1, v2, and future-version profiles. The staleness contract is now: every cache consumer (repository producer, worker, controller, planning helper, scan lookup) enforces exact-version equality; display alone is version-agnostic.

## Round 4 — Codex (effort: high)

Remaining finding addressed. No new material problems. Non-blocking detail adopted:
rollout SQL uses COALESCE(json_extract(...), 1) so legacy JSON without the field counts as v1.

VERDICT: APPROVED
