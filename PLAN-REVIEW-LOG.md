# Plan Review Log: Recalibrate spectral color classification

Act 1 (grill) complete — plan locked with the user. MAX_ROUNDS=5.
Reviewer model: gpt-5.6-sol (config default) — codex-cli 0.144.6.

## Round 1 — Codex

1. BUG — scoring incorrectly declared unaffected: `dominant_color` drives `_spectral_color_penalty` (scoring.py:320-330), so recalibration can change transition scores/ordering.
2. BUG — "ignored on read" conflicts with validate-first deserialization: validating `SpectralProfile` first still rejects missing/invalid persisted `dominant_color`. Parse JSON, replace field, then validate.
3. RISK — exact equal-excess ties undefined (dict order would accidentally decide). Define deterministic tie policy + tests.
4. RISK — empirical acceptance not reproducible: no tolerance, dataset identity, or query specified.
5. BUG — repository governance absent: plan lacks OpenSpec/SDD artifacts and six-command verification sequence.

VERDICT: REVISE

### Claude's response

- Finding 1 ACCEPTED (verified with nuance): `_spectral_color_penalty` reads `dominant_color` but is inactive under the default config (`spectral_cohesion = 0.0`, scoring.py:90). Plan now states the real blast radius and adds a scoring regression test.
- Finding 2 ACCEPTED: deserialization order fixed in the plan — parse dict, overwrite `dominant_color`, validate once; tests added for stale/missing/invalid values.
- Finding 3 ACCEPTED: exact ties resolve RED > GREEN > BLUE, with exact-tie and near-tie boundary tests.
- Finding 4 ACCEPTED (scoped): validation now names the DB, denominator, exact expected counts for the frozen 10,390-profile snapshot, and a ±2pp tolerance if the library drifts; results recorded in this log, no library data committed.
- Finding 5 REJECTED: process governance (SDD/OpenSpec artifacts, verification gates) is orchestration-level workflow chosen by the user, not plan content for this skill's flow. The plan already mandates strict TDD; how the work is routed (SDD cycle vs direct build) is decided at implementation sign-off.

## Round 2 — Codex

Prior findings (deserialization, tie-break, empirical validation, scoring impact) addressed. One remaining:

1. BUG — "inactive under the default config" is false for the desktop app: `AppSettings` defaults `spectral_cohesion` to 0.5 and the Build screen slider initializes at 50%, so recalibration affects recommendation ordering for default users.

VERDICT: REVISE

### Claude's response

- Finding ACCEPTED (verified: `config/settings.py:37` defaults 0.5; `build_screen.py:107` slider at 50). Claude's Round-1 nuance was wrong — the internal `TransitionScoringConfig` 0.0 default is not what desktop users get. Plan now states the effective desktop default is 0.5, accepts the ordering change as intended, and adds a regression test through the default settings-to-recommendation path.

## Round 3 — Codex

Remaining finding addressed (internal 0.0 vs effective desktop 0.5 default distinguished, settings-driven regression coverage added). No new material problems.

VERDICT: APPROVED
