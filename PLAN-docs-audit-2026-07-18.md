# Plan: Fix stale accuracy issues in onboarding docs
_Locked via grill — by Claude + Freddy_

## Goal
README.md and AGENTS.md contain factual claims that no longer match the repository's current state. Fix both so the documentation stops drifting out of sync with reality, without touching CONTRIBUTING.md or SECURITY.md (verified clean) or the rest of `docs/` (out of scope — internal engineering artifacts, not user onboarding surface).

## Approach

1. **README.md:558** (English) — Replace `**Test suite**: 778 tests, all passing. Strict TDD is enforced for all changes.` with a command-based line that doesn't hardcode a count, and scope the TDD claim to match AGENTS.md:16 ("every behavior-changing task"): `**Test suite**: run \`uv run pytest -q\` for current status. Strict TDD is enforced for behavior-changing changes.`

2. **README.md:1190** (Spanish) — Replace `**Suite de tests**: 734 tests, todos pasando. Se aplica TDD estricto para todos los cambios.` with the equivalent command-based, scope-corrected line: `**Suite de tests**: ejecutar \`uv run pytest -q\` para ver el estado actual. Se aplica TDD estricto para cambios que modifican comportamiento.`

3. **AGENTS.md:3** — Replace `> This \`AGENTS.md\` governs the entire \`/Users/freddymolina/Documents/audio\` tree.` with a repo-relative statement that doesn't depend on the local clone path, e.g. `> This \`AGENTS.md\` governs this repository root and its subdirectories.`

## Key decisions & tradeoffs

- **Command-over-count for test suite**: chosen instead of updating the number to 1006, because the number has already gone stale twice (778 → 734, both wrong against the real 1006). A command reference has no expiry date; the tradeoff is it's slightly less immediately informative than a number, but the number was actively misleading.
- **Repo-relative path over absolute path**: AGENTS.md:3 named an absolute path belonging to a *different, independent* git checkout (`/Users/freddymolina/Documents/audio`, confirmed via its own `.git`), not a parent or submodule of this repo. Hardcoding this repo's own absolute path would fix it for one user's machine but break again for any other clone location. A repo-relative phrasing removes the dependency on any specific filesystem layout.
- **Scope limited to README.md + AGENTS.md**: CONTRIBUTING.md and SECURITY.md were audited and contain no verifiable discrepancies against current repo state — no edits proposed for them.

3. **tests/test_public_open_source_docs.py** — Extend the existing docs-guard test file (already checks README/CONTRIBUTING/SECURITY/NOTICE via `required_fragments`/`forbidden_fragments`) to prevent this class of drift from recurring:
   - Add a regex assertion scoped to the `**Test suite**` / `**Suite de tests**` line specifically (not just the "all passing"/"todos pasando" phrasing, so any hardcoded count on that line is caught) asserting no `\d+\s+tests` pattern appears on it, in either language section.
   - Add `AGENTS` to the module's tracked docs and a new `test_agents_governs_repo_root_without_hardcoded_path()` asserting the file contains `"governs this repository root"` and does not contain `"/Users/"`.

4. **Verification** — Per AGENTS.md:53-66, run the full mandatory ordered sequence (these commands touch a modified Python test file, so pyright/ruff/coverage are all relevant, not just pytest):
   ```
   uv run pytest -q
   uv run pyright src tests
   uv run pytest --cov --cov-fail-under=70 -q
   uv run ruff check .
   uv run ruff format --check .
   uv run python scripts/release_gate_check.py --run
   ```

## Risks / open questions
- None identified — the doc edits are isolated text replacements; the test addition follows an existing, established pattern in the same file (no new tooling introduced).

## Out of scope
- CONTRIBUTING.md, SECURITY.md (verified accurate, no changes)
- Remaining `docs/` files (HELP-N specs, handoffs, packaging/release artifacts) — internal engineering docs, not user onboarding surface; excluded per scope decision at grill start
- Style/wording/structure improvements to README.md or AGENTS.md beyond the two accuracy fixes above
