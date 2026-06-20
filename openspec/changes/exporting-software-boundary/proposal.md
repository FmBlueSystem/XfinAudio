# Proposal: Exporting software boundary

## Intent

Extract the supported playlist-file export software catalog from export planning/application dispatch into a pure exporting module, and tighten filename generation so empty sanitized suffixes do not create empty filename parts.

## Scope

In scope:
- Add a pure `xfinaudio.exporting.software` module for playlist-file export extension lookup.
- Use that module from export planning and application writer dispatch.
- Add focused tests for the catalog and empty sanitized suffix behavior.

Out of scope:
- Changing Serato/Rekordbox/Traktor/VirtualDJ file formats.
- Adding new export targets.
- UI behavior changes.
- Audio/DSP changes.
- Serato DB V2 writes.
