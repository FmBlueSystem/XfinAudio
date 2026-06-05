# Pull request

## Summary

- 

## Scope and review notes

- What changed:
- What is intentionally out of scope:
- Reviewer should check first:

## Tests run

Check every command you ran and paste failures if any:

- [ ] `uv run pytest -q`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] Focused tests:
- [ ] Manual QA, if relevant:

## Safety checklist

- [ ] No audio mutation.
- [ ] No live Serato database V2 mutation.
- [ ] Writes are limited to app-owned database, settings, or export files.
- [ ] No private audio files, private library databases, or sensitive local paths are included.

## GPLv3 and open-source review

- [ ] GPL-3.0-only and open-source documentation are unchanged or updated where relevant.
- [ ] Third-party dependency/license documentation is unchanged or updated where relevant.
- [ ] No binary, release, or legal clearance claims are made.

## Release gates

- [ ] Not relevant.
- [ ] Relevant: `.github/workflows/non-audio-release-gates.yml` and related evidence/docs were reviewed.
- [ ] Packaging or release behavior changed; describe the extra release gate/manual review needed:
