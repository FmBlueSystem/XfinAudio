# Spec: Multi-Software DJ Export

## Overview

Extend XfinAudio's export capability so DJs can send playlists to Pioneer DJ Rekordbox, Native Instruments Traktor, and VirtualDJ — in addition to the existing Serato crate export.

## Functional Requirements

### FR-1: Software Selector
- The Export screen must display a selector with at least four options: Serato, Rekordbox, Traktor, VirtualDJ.
- The default selection is Serato (preserves existing behavior).
- Changing the selector updates the preview/export button labels.

### FR-2: Rekordbox Export
- Generate a `.xml` file compatible with Rekordbox's `DJ_PLAYLISTS` format (Version 1.0.0).
- Include a `COLLECTION` with one `TRACK` per playlist track.
- Include a `PLAYLISTS/NODE/NODE` playlist leaf referencing tracks by `TrackID`.
- Encode track locations as `file://localhost/...` URIs.
- XML-escape special characters (`&`, `<`, `>`, `'`, `"`).

### FR-3: Traktor Export
- Generate a `.nml` file with root `<NML VERSION="19">`.
- Include `<HEAD COMPANY="www.native-instruments.com" PROGRAM="Traktor"/>`.
- Include `<COLLECTION ENTRIES="N">` with one `<ENTRY>` per track.
- Each entry contains `<LOCATION FILE="..." DIR="..." VOLUME="osx"/>`.
- DIR uses Traktor's `:`-separated format (e.g., `/:music/:` for `/music`).
- Include `<TEMPO BPM="..." BPM_QUALITY="100.000000"/>` when BPM is available.
- Include `<MUSICAL_KEY VALUE="..."/>` when key is available.
- Include a `<PLAYLISTS>/<NODE TYPE="PLAYLIST" NAME="...">` with entries.

### FR-4: VirtualDJ Export
- Generate a `.xml` file with root `<VirtualFolder ordered="yes">`.
- Include one `<song>` element per track with attributes:
  - `path` (absolute file path, required)
  - `title`, `artist`, `bpm`, `key` (optional but populated when available)
  - `idx` (0-based playlist order)

### FR-5: Export Routing
- `ExportScreen.preview_requested` and `export_requested` are routed through `MainWindow.preview_export()` and `MainWindow.export_recommendation()`.
- These methods dispatch to the exporter matching the selected software.
- Serato path is unchanged and continues to use the existing crate writer.

### FR-6: Path Handling
- All exporters receive absolute file paths from `TrackRecord.path`.
- Each exporter converts paths to its target format internally.
- No file is moved or copied; only playlist metadata files are written.

### FR-7: Error Handling
- If no recommendation exists, show "Generate a recommendation before exporting to {software}".
- If readiness is `blocked`, block export for all software (same as Serato).
- If safe export folder is not set, block non-Serato exports with a clear message.
- If the selected software is unknown, show "Unknown export software: {software}".

## Non-Functional Requirements

- NFR-1: Exporters must be pure functions (deterministic, no side effects) except for file I/O in `write_*` helpers.
- NFR-2: All XML output must use UTF-8 encoding.
- NFR-3: New code follows strict TDD.

## Data Model

- Input: `PlaylistRecommendation` (existing)
- Output per software:
  - Rekordbox: UTF-8 XML string / `.xml` file
  - Traktor: UTF-8 NML string / `.nml` file
  - VirtualDJ: UTF-8 XML string / `.xml` file

## UI Layout

```
+----------------------------------------------------------+
|  Variant: none           [Serato ▼]          [Choose...] |
+----------------------------------------------------------+
|  ... guidance labels ...                                 |
|  [Preview Serato Export] [Export to Serato]              |
+----------------------------------------------------------+
```

When selector changes to Rekordbox:
```
|  [Preview Rekordbox Export] [Export to Rekordbox]        |
```

## Dependencies

- `PlaylistRecommendation`
- `TrackRecord`
- Existing Serato export infrastructure
- `xml.etree.ElementTree` (stdlib)
