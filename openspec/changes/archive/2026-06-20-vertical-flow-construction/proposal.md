# Proposal: Vertical flow construction foundation

## Intent

Build the next XfinAudio product increment as a complete vertical workflow instead of isolated UI or package edits.

The first construction path is:

```text
Library Scan -> Recommendation -> Playlist Save/Export
```

This path is the product backbone because it crosses Presentation, Presentation Adapters, Application, Domain, Ports, and Infrastructure.

## Problem

The architecture minimum has been reached for removing the legacy shell layout graft surface, but the product can regress if new work is added directly into desktop widgets or MainWindow orchestration.

The next construction step needs an explicit vertical-flow boundary so future feature work grows through use cases and testable contracts instead of rebuilding UI-heavy coupling.

## Scope

In scope:

- Define the first vertical product workflow around scan, recommendation, save, and export.
- Keep UI rendering and user interaction in `xfinaudio.desktop`.
- Put cross-module orchestration in `xfinaudio.application`.
- Keep recommendation/export/readiness policy in domain packages.
- Use ports where persistence/export/settings/audio boundaries need substitution in tests.
- Add focused tests before behavior-changing implementation.

Out of scope:

- UI redesign.
- New recommendation algorithms.
- New DSP, waveform, beat, cue, phrase, rendering, time-stretching, or pitch-shifting scope.
- Live Serato DB V2 writes.
- Audio file mutation.
- Packaging or release publication changes.

## Success Criteria

- A durable vertical-flow contract exists in OpenSpec.
- The next implementation slice has a clear RED -> GREEN -> REFACTOR path.
- UI remains thin: widgets/screens do not own product decisions.
- Application use cases orchestrate scan/recommend/save/export boundaries.
- Verification can be run with focused unit tests and the standard release gates.

## Rollback

The initial slice is planning-only and can be reverted by removing `openspec/changes/vertical-flow-construction/` before implementation begins.
