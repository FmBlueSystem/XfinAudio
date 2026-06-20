# Archive Report: Core lazy exports

Status: archived
Archived: 2026-06-20
Change: core-lazy-exports

## Summary

The `core-lazy-exports` OpenSpec change is archived after implementation PR #246 merged to `main` and post-merge main CI passed.

## Result

`xfinaudio.library` and `xfinaudio.audio` public package exports now resolve lazily. Pure imports of `xfinaudio.library.models` and `xfinaudio.audio.analysis_planning` no longer load scan services, repositories, batch analyzers, or spectral profile modules as package-import side effects.

## Archive Gate Evidence

- `tasks.md` has all lifecycle tasks checked.
- `verify-report.md` records RED, GREEN, focused evidence, full local gates, and release gate evidence.
- Durable spec exists at `openspec/specs/core-lazy-exports/spec.md`.
- Active change folder moved to `openspec/changes/archive/2026-06-20-core-lazy-exports/`.

## Implementation and CI Evidence

- Issue: [#245](https://github.com/FmBlueSystem/XfinAudio/issues/245)
- Implementation PR: [#246](https://github.com/FmBlueSystem/XfinAudio/pull/246)
- Main commit after merge: `81e2bc73585d72ab2fca5f280ab860ae57fa2456`
- PR CI run: `27876704565` passed.
- Post-merge main CI run: `27876763036` passed in 2m6s.

## Safety

Archive-only closeout.

- No production code changes in this archive PR.
- No tests changed in this archive PR.
- No dependency changes.
- No audio files mutated.
- No DSP scope added.
- No live Serato DB V2 writes.
- No export format changes.
- No project-root `build/` or `dist/` artifacts.
