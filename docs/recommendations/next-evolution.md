# XfinAudio — Next Evolution Recommendations

> Author: Freddy Molina — BlueSystem.io (Audio Division)
> Date: 2026-06-07
> Status: **All recommendations implemented and archived** (2026-06-08)

---

## Context

XfinAudio has reached a mature baseline:

- ✅ Full i18n (English / Spanish)
- ✅ Metadata-first library with scan, filter, sort, duration
- ✅ Deterministic recommendation with explainable scoring
- ✅ DJ Prep Copilot with Safe / Balanced / Adventurous variants
- ✅ Serato crate export with safety guards
- ✅ PyInstaller `.app` bundle for macOS
- ✅ Corporate branding (BlueSystem.io, Freddy Molina)
- ✅ **Audio Preview** (integrated QMediaPlayer, library-table play/pause)
- ✅ **Playlist Persistence** (SQLite, My Playlists screen, drag-and-drop editor)
- ✅ **Multi-Software Export** (Serato, Rekordbox, Traktor, VirtualDJ)
- ✅ **Live Assistant Mode** (Now Playing, Next Suggestions, Set History, risk alerts)
- ✅ **734 passing tests**, strict TDD history

The app is a solid **preparation tool**. The next evolution must close the gap between "seeing numbers" and "hearing music" — because a DJ chooses tracks with ears first, spreadsheets second.

---

## Recommendation A — Audio Preview / Reproductor integrado (Recommended)

**What:** A lightweight audio player inside XfinAudio so DJs can listen to track previews directly from the library table, without leaving the app.

**Why it matters:**
- A DJ does not pick tracks by numbers alone. BPM, key, and energy scores are necessary but not sufficient.
- Currently the DJ must open Serato or another player to validate that a transition "sounds" right.
- Audio preview closes the decision loop: **see metadata → hear preview → decide**.
- It is the natural bridge toward a future "Live Assistant" mode.

**Scope:**
- Play / Pause button per track row in the library table
- Position slider + current time / total duration display
- Volume control (independent from system volume)
- Optional: preview from cue point if metadata contains one
- Optional: waveform thumbnail from existing metadata (not DSP analysis)

**Technical approach:**
- Use `QMediaPlayer` (already included in PySide6 — zero new dependencies)
- Audio playback is read-only; no audio mutation, no analysis, no mixing
- Player state lives outside Qt logic where possible; UI is thin

**Complexity:** Medium
**Risk:** Low (PySide6 native component, no DSP scope)
**User impact:** Very High

---

## Recommendation B — Playlist Persistence and Editing

**What:** Save generated playlists into the SQLite database, allowing the DJ to return later, edit order, add/remove tracks, rename, and re-export.

**Why it matters:**
- Currently a playlist is generated, reviewed, exported to Serato… and lost.
- DJs prepare sets over days or weeks, not in a single session.
- A DJ may want to maintain multiple set versions for the same gig.

**Scope:**
- New `playlists` table in SQLite
- "My Playlists" screen with saved set list
- Open a saved playlist in edit mode (drag-and-drop reorder)
- Add tracks from library into an open playlist
- Remove tracks from a playlist without deleting from library
- Rename / duplicate / delete playlists
- Export a saved playlist to Serato at any time

**Technical approach:**
- Pure SQLite schema extension; no new dependencies
- Drag-and-drop uses Qt's built-in `QTableWidget` reordering
- Playlist records reference `TrackRecord` by path (same foreign key strategy)

**Complexity:** Low-Medium
**Risk:** Low
**User impact:** High

---

## Recommendation C — Multi-Software DJ Export

**What:** Export playlists to Pioneer DJ Rekordbox, Native Instruments Traktor, and VirtualDJ — not only Serato.

**Why it matters:**
- Serato is large but not universal. Rekordbox is the club standard in many venues.
- Traktor is common in electronic music production. VirtualDJ is entry-level dominant.
- Expanding export targets multiplies the addressable user base.

**Scope:**
- Rekordbox: export to `.xml` playlist format
- Traktor: export to `.nml` (Native Music Library)
- VirtualDJ: export to folder/database format
- Software selector in the Export screen
- Path conversion logic per target (each uses different relative path conventions)

**Technical approach:**
- Each exporter is a deterministic byte/text builder (same pattern as Serato crate writer)
- No database mutation on any target; only write playlist files
- Requires research into each format's specification

**Complexity:** Medium-High
**Risk:** Medium (format specs may be undocumented or change)
**User impact:** High (market expansion)

---

## Recommendation D — Live Assistant Mode

**What:** A simplified performance view that the DJ uses **while playing**. Shows current track, recommends next tracks in real time, and alerts on risky transitions.

**Why it matters:**
- This evolves XfinAudio from "prep tool" to "performance assistant".
- In the booth, the DJ has no time to browse tables and filters.
- A clean heads-up display with "next best 3 candidates" reduces cognitive load under pressure.

**Scope:**
- "Now Playing" panel: current track + key / BPM / energy
- "Next Suggestion" panel: top 3 candidates with scores
- Alert badge if a candidate breaks BPM guardrail (>3%) or key clash
- "Load Next" button (marks as loaded, does not play audio)
- Set history timeline (tracks played in this session)
- Optional: auto-advance suggestions as tracks are marked loaded

**Technical approach:**
- Reuses existing recommendation engine with a real-time "current track" anchor
- Thin Qt view; all logic is deterministic scoring already tested
- May require background re-scoring thread for responsiveness

**Complexity:** High
**Risk:** High (changes app architecture from prep to performance)
**User impact:** Very High (product category expansion)

---

## Recommended Sequence

| Phase | Recommendation | Rationale |
|---|---|---|
| **1** | **A — Audio Preview** | Closes the most critical user loop. No new dependencies. Sets foundation for D. |
| **2** | **B — Playlist Persistence** | Natural follow-up: now that the DJ can preview, they want to save and refine playlists. |
| **3** | **C — Multi-Software Export** | Once playlists are saved and refined, DJs want to use them in their software of choice. |
| **4** | **D — Live Assistant** | The capstone: a performant, preview-tested, persistable playlist becomes a live recommendation engine. |

---

## Decision Log

| Date | Decision | By |
|---|---|---|
| 2026-06-07 | Select Option A (Audio Preview) as next SDD change | Freddy Molina |
| 2026-06-07 | Defer Live Assistant (D) until Audio Preview + Playlist Persistence are shipped | Freddy Molina |
| 2026-06-07 | Multi-software export (C) is valuable but lower priority than closing the preview loop | Freddy Molina |
| 2026-06-08 | All four recommendations (A, B, C, D) implemented, tested, and archived | Freddy Molina |

---

## Appendix: Technical Constraints

- No audio DSP (BPM detection, key detection, waveform analysis) — out of scope per project non-goals.
- No AI generation or black-box recommendations — scoring remains deterministic and explainable.
- All new features must follow strict TDD (RED → GREEN → REFACTOR).
- Review budget: 400 changed lines per PR slice.
- Chained PRs recommended for any change exceeding the review budget.
