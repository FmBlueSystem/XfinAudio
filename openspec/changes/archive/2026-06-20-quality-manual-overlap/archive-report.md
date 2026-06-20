# Archive Report: Quality manual overlap

Status: archived
Archived: 2026-06-20
Change: quality-manual-overlap

## Summary

The `quality-manual-overlap` OpenSpec change is archived after implementation PR #238 merged to `main` and post-merge main CI passed.

## Result

Recommendation quality reports now compute `manual_overlap_ratio` against distinct manual reference paths. Duplicate manual reference paths no longer artificially lower the overlap denominator.

The slice also removed import-time coupling from package-level recommendation/exporting barrels by preserving public exports through lazy package resolution.

## Archive Gate Evidence

- `tasks.md` has all lifecycle tasks checked.
- `verify-report.md` records RED, GREEN, focused evidence, full local gates, and release gate evidence.
- Durable spec exists at `openspec/specs/quality-manual-overlap/spec.md`.
- Active change folder moved to `openspec/changes/archive/2026-06-20-quality-manual-overlap/`.

## Implementation and CI Evidence

- Issue: [#237](https://github.com/FmBlueSystem/XfinAudio/issues/237)
- Implementation PR: [#238](https://github.com/FmBlueSystem/XfinAudio/pull/238)
- Main commit after merge: `ac461e247dc465d7a0e42bedcfbb4e6a142a25a7`
- PR CI run: `27875764308` passed.
- Post-merge main CI run: `27875822238` passed in 3m12s.
- Archive local gate: `uv run python scripts/release_gate_check.py --run` passed after archive move.

## Safety

Archive-only closeout.

- No production code changes in this archive PR.
- No tests changed in this archive PR.
- No dependency changes.
- No audio files mutated.
- No DSP scope added.
- No live Serato DB V2 writes.
- No project-root `build/` or `dist/` artifacts.
