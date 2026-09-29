# Feature: v2 release-gate remediation — gate green + process guard

## Goal

Resolve the confirmed process failure: tag v2.0.0 (pushed to GitHub, DMG built)
does not pass its own release gate. Make the candidate green, render the gate
evidence that was never produced, and add a structural guard so a version bump
cannot ship again without fresh gate evidence.

## Context

- Discovered 2026-09-28 running `scripts/release_gate_check.py --run` on
  main@5ca3433 (= origin/main = tag v2.0.0): FAIL type-check, 11 pyright
  errors in 5 test files. Tests+coverage PASS (gate order runs them first).
- Errors are typing looseness in tests (SimpleNamespace payloads, object->
  typed params, variadic vs 6-tuple TIV, list[int | None] vs sorted/min/max).
  No runtime bugs; 2435 tests green.
- Ledger `version-2-scientific-foundation.md` claims "ruff/pyright clean
  repo-wide" for the slices — verified per-slice on the working branch, but
  the final tagged candidate was never gate-checked. Root process gap.
- Release is public: tag v2.0.0 on origin, out/XfinAudio-2.0.0.dmg built.

## Tasks

1. [x] R1 fix the 11 pyright errors in tests (minimal typing changes only, no
       behavior edits). DONE: commit 46fa8dd — typing-only, 6 files;
       pyright 0 errors, targeted suite 360 passed.
2. [x] R2 full gate green on the fix branch. DONE: commit f1e0d31 (ruff format
       on 10 pre-existing deviating files, format-only) + full
       `release_gate_check.py --run` all PASS; evidence committed at
       docs/reviews/2026-09-v2-gate-remediation/ (README + JSON). Manual MIK QA
       gate: COMPLETED.
3. [x] R3 structural guard. DONE, adjusted to the facts: publish-to-pypi.yml
       ALREADY gated the publish (v2.0.0 tag run 36417902188 failed at the
       gate step; PyPI never received the release). The real gaps were the
       unattended red CI on main and the ungated local DMG. Added the explicit
       rule to AGENTS.md (commit fa7ec42): red gate on main blocks any tag,
       bump, or DMG. Fix-forward executed: main @ fc88e70 (bump 2.0.1), local
       tag v2.0.1 created; push pending user authorization.

## Evidence

- 46fa8dd fix(tests): tighten typing to satisfy pyright on the v2.0.0 candidate
- f1e0d31 style(tests): apply ruff format to 10 files deviating from the formatter
- 7b395a4 docs(release): record v2.0.0 gate remediation evidence
- fa7ec42 docs(process): a red gate on main blocks any release cut
- fc88e70 → amended as c700bdb chore(release): bump version to 2.0.1 (tag
  v2.0.1); main pushed to origin, CI green (run 36501954792). Publish workflow
  gate PASSED on the tag but PyPI upload failed 403: the repo's
  PYPI_API_TOKEN secret is expired/invalid — owner-side action, run
  36501957014 re-runnable after the secret is fixed (no new tag needed).
- Gate evidence: docs/reviews/2026-09-v2-gate-remediation/release-gate-evidence.json
