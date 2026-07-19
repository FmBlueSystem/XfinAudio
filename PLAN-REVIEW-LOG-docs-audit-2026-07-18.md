# Plan Review Log: Fix stale accuracy issues in onboarding docs
Act 1 (grill) complete — plan locked with the user. MAX_ROUNDS=5.
Reviewer model: gpt-5.6-sol (config default, reasoning effort: low) — codex-cli 0.144.6.

## Round 1 — Codex

1. BUG — PLAN.md:9–11: replacement text preserved "Strict TDD is enforced for all changes," but AGENTS.md:14–17 scopes strict TDD to behavior-changing tasks only. Fix: scope the claim in both language versions.
2. RISK — PLAN.md:21–22: no verification step to prevent future drift (stale counts, absolute paths). Fix: add regression checks rejecting hardcoded README test counts and absolute clone paths.

Key learnings noted by Codex: current suite collects 1006 tests; doc accuracy needs durable regression checks, not just one-time replacements.

VERDICT: REVISE

### Claude's response
- Finding 1: verified against AGENTS.md:16 ("every behavior-changing task follows RED → GREEN → REFACTOR → VERIFY") — confirmed real discrepancy, in scope (precision issue in an in-scope file). Incorporated: both README replacement lines (EN/ES) now scope the TDD claim to "behavior-changing changes" instead of "all changes."
- Finding 2: rejected. Adding regression tests/lint checks is a legitimate idea but expands scope from "edit 2 doc lines" to "build new test infrastructure," which the user did not ask for and wasn't part of the locked plan scope (concrete doc edits only). Logged as a follow-up suggestion in PLAN.md instead of implementing it here.

## Round 2 — Codex

- Prior finding 1 — addressed: README now correctly scopes strict TDD to behavior-changing changes.
- Prior finding 2 — unresolved: PLAN.md rejects the regression guard even though drift already recurred twice. Fix: add forbidden-fragment assertions to tests/test_public_open_source_docs.py.
- New RISK: plan specifies no post-edit verification despite AGENTS.md:53-66 requiring it. Fix: add the focused documentation test plus the repository's required verification commands.

Key learning noted by Codex: one-time replacements correct drift but do not prevent recurrence.

VERDICT: REVISE

### Claude's response
- Reversed my Round 1 rejection after checking the actual repo state: tests/test_public_open_source_docs.py already exists and already tests README/CONTRIBUTING/SECURITY/NOTICE via required_fragments/forbidden_fragments lists. My Round 1 premise ("this requires building new test infrastructure") was wrong — it's a 2-3 line extension of an established, already-in-use pattern in the exact file that already covers README.md. Incorporated as PLAN.md step 3: a regex guard against hardcoded test counts in README.md, plus a new small test asserting AGENTS.md governs "this repository root" and contains no "/Users/" absolute path.
- Also incorporated the new verification-step risk as PLAN.md step 4, per AGENTS.md's own "smallest relevant pytest target first, then full suite" guidance.

## Round 3 — Codex

- Prior findings addressed: TDD scope corrected, regression coverage included.
- BUG — PLAN.md:25: verification step cited AGENTS.md:53-66 but only listed pytest, omitting the mandatory pyright/coverage/ruff/release-gate commands. Fix: include the full ordered sequence from AGENTS.md:58-63.
- RISK — PLAN.md:22: the regex only rejected counts followed by "all passing"/"todos pasando" — a differently-phrased hardcoded count would slip through. Fix: reject any numeric test count on the Test suite / Suite de tests line itself, not just that exact phrasing.

VERDICT: REVISE

### Claude's response
- Both accepted, no scope concerns — both are proportionate refinements of steps already in the plan, not new work. Step 4 now lists the full AGENTS.md verification sequence (justified: the change touches a Python test file, so pyright/ruff/coverage are legitimately relevant, not just pytest). Step 3's regex is now scoped to the Test suite/Suite de tests line and checks for any digit + "tests" pattern on it, not just the one exact phrase.

## Round 4 — Codex

All prior material findings addressed: TDD scope matches AGENTS.md, regression coverage rejects any hardcoded count on the suite-status lines, complete mandatory verification sequence included. No new material risks found.

VERDICT: APPROVED

## Resolution
Converged after 4 rounds. Plan approved by Claude (Act 1 grill) and Codex (Act 2 adversarial review, gpt-5.6-sol).

## Act 3 — Build (Claude, direct implementation)

Implemented all 4 approach steps as written:
1. README.md:558 (EN) — test-count line replaced with `uv run pytest -q` reference, TDD scope corrected.
2. README.md:1190 (ES) — same fix, Spanish.
3. AGENTS.md:3 — governance line changed to repo-relative wording.
4. tests/test_public_open_source_docs.py — added `AGENTS` to `PUBLIC_DOCS`, added regex guard against hardcoded `\d+ tests` on the suite-status line in README, added `test_agents_governs_repo_root_without_hardcoded_path()`.

Verification (full AGENTS.md:58-63 sequence, all green):
- `uv run pytest -q` → 1007 passed (1006 prior + 1 new test)
- `uv run pyright src tests` → 0 errors, 0 warnings
- `uv run pytest --cov --cov-fail-under=70 -q` → 90.27% coverage, gate passed
- `uv run ruff check .` → all checks passed
- `uv run ruff format --check .` → 263 files already formatted
- `uv run python scripts/release_gate_check.py --run` → all gates PASS

Status: DONE.
