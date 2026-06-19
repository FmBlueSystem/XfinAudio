# Proposal: Application Playlist File Export Use Case

## Intent
Strengthen the Application layer by moving non-Serato playlist file export orchestration out of the desktop coordinator into a UI-independent use case.

## Scope
- Add an application-level use case for non-Serato playlist file export planning and writer dispatch.
- Keep UI copy, labels, dialogs, selected software reading, and error rendering in `desktop`.
- Preserve existing Rekordbox, Traktor, and VirtualDJ export behavior.

## Out of Scope
- Serato crate export, readiness sidecars, and Serato DB V2 behavior.
- Export file format changes.
- UI redesign or copy changes.
- Audio mutation or DSP scope.

## Success Criteria
- Desktop no longer dispatches non-Serato writer functions directly.
- Application use case can be tested with fake writers before production code changes.
- Existing export coordinator behavior remains green.
