# Proposal: XfinAudio Multi-Software DJ Export

## What

Extend the Export screen so DJs can export playlists to Pioneer DJ Rekordbox, Native Instruments Traktor, and VirtualDJ — not only Serato.

## Why it matters

- Serato is large but not universal. Rekordbox is the club standard in many venues.
- Traktor is common in electronic music production. VirtualDJ is entry-level dominant.
- Expanding export targets multiplies the addressable user base and makes XfinAudio useful regardless of the DJ's software of choice.

## Scope

- Rekordbox: export to `.xml` playlist format
- Traktor: export to `.nml` (Native Music Library) playlist format
- VirtualDJ: export to folder/list XML format
- Software selector in the Export screen
- Path conversion logic per target (each uses different relative path conventions)
- No database mutation on any target; only write playlist files

## Out of scope

- Automatic library database sync
- Writing to proprietary binary formats
- Real-time bidirectional sync

## Technical approach

- Each exporter is a deterministic text/XML builder (same pattern as Serato crate writer)
- `ExportScreen` adds a software selector QComboBox
- MainWindow routes export actions to the selected exporter
- Reuses existing `PlaylistRecommendation` as input

## Complexity

Medium-High

## Risk

Medium (format specs may be undocumented or change)

## User impact

High (market expansion)

## Dependencies

- Existing Serato export infrastructure
- Existing `PlaylistRecommendation` model

## Acceptance criteria

- [ ] Export selector shows Serato, Rekordbox, Traktor, VirtualDJ
- [ ] Rekordbox XML is valid for import into rekordbox
- [ ] Traktor NML is valid for import into Traktor
- [ ] VirtualDJ list XML is valid for import into VirtualDJ
- [ ] Path conversion handles macOS/Windows differences per target
- [ ] All new code covered by strict TDD
- [ ] Full test suite passes with 0 regressions
