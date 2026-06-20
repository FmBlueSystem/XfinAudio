# Proposal: Library scan planning boundary

## Intent

Extract the pure library scan candidate planning rule from `library.scan_service` so candidate selection can be tested and improved without invoking metadata readers, spectral analyzers, UI, or persistence.

## Problem

`scan_folder()` currently owns both candidate planning and execution. That keeps supported-extension filtering close to Mutagen/librosa execution and also allows duplicate candidate paths from an injected lister to be processed more than once.

## Scope

In scope:
- Introduce a pure `xfinaudio.library.scan_planning` module.
- Move supported-extension ownership and candidate planning into that module.
- Use the planner from `scan_service` and `config.settings`.
- Add focused unit tests proving duplicate candidates are collapsed before metadata reads.

Out of scope:
- New DSP features.
- Audio mutation.
- Serato DB V2 writes.
- Export format changes.
- UI behavior changes.
- Real filesystem scanning semantics beyond candidate planning.

## Success criteria

- Scan candidate planning is importable without Mutagen/librosa/PySide6 execution.
- Duplicate candidate paths are read once and produce one record.
- Existing scan behavior and release gates continue to pass.
