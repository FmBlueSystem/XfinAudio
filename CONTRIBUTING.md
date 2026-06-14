# Contributing to XfinAudio

Thanks for helping improve XfinAudio. Keep changes small, tested, and aligned with the app's non-destructive DJ playlist assistant scope.

## Development setup

Requirements: Python 3.11 and `uv`.

```bash
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

For focused work, run the smallest relevant pytest target first, then run the full suite before handing off.

Before source repository publication work, follow `docs/repository-publication-checklist.md` so publication stays source-only and does not imply binary readiness or legal clearance.

## Methodology: gentle-ai SDD/TDD

This project follows **gentle-ai Spec-Driven Development / Test-Driven Development** for every behavior change, feature, non-trivial refactor, and bug fix.

- **SDD** means every change produces durable artifacts under `openspec/`: `proposal.md`, `spec.md`, `design.md`, `tasks.md`, `apply-progress.md`, and `verify-report.md`.
- **TDD** means every behavior-changing task follows RED → GREEN → REFACTOR → VERIFY.
- **gentle-ai** means changes are executed incrementally through explicit phase gates, not as one large patch.

For the detailed lifecycle, rules, and state artifact template, see the project skill:

- `.atl/skills/gentle-ai-sdd-tdd/SKILL.md`

## SDD/TDD expectation

Use test first development for behavior changes and bug fixes:

1. Add or update a failing test for the intended behavior.
2. Verify the test fails for the expected reason.
3. Implement the smallest change that makes it pass.
4. Refactor while keeping tests green.
5. Run focused tests, then the full verification commands above.

For changes that touch product behavior, also create or update the required `openspec/` artifacts and keep each review slice within the 400-line budget. If the change exceeds that budget, plan chained PRs.

## Safety constraints

Do not expand scope without explicit discussion. Required boundaries:

- No audio mutation.
- No live Serato database V2 mutation.
- No DSP, audio rendering, mixing, time-stretching, pitch-shifting, waveform analysis, key detection, BPM detection, beat tracking, or cue/phrase detection.
- App writes must stay limited to app-owned database, settings, and export files.
- Serato crate writes must stay behind the documented explicit safe export/backup/validation flow.
- Do not create release artifacts, signing claims, notarization claims, or DMG completion claims in normal development changes.

## Issues

Good issues include:

- the user-facing workflow or safety concern;
- current behavior and expected behavior;
- reproduction steps or fixture details that do not require private audio libraries;
- relevant logs without secrets or personal library paths when possible.

## Pull requests

Pull requests should include:

- a concise summary of the change;
- RED/GREEN test evidence for behavior changes;
- commands run and results;
- explicit notes for any safety, Serato export, dependency, or packaging impact;
- confirmation that no project-root `build/` or `dist/` artifacts were created.

Keep documentation claims conservative. No legal advice or legal clearance is implied by project docs or PR text.
