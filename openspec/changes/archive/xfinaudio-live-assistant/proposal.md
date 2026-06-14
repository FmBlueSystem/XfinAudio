# Proposal: XfinAudio Live Assistant Mode

## What

A simplified performance view that the DJ uses **while playing**. Shows the current track, recommends the next tracks in real time, and alerts on risky transitions. This evolves XfinAudio from a "prep tool" to a "performance assistant".

## Why it matters

- In the booth, the DJ has no time to browse tables and filters.
- A clean heads-up display with "next best 3 candidates" reduces cognitive load under pressure.
- Audio preview (Option A) and playlist persistence (Option B) have closed the preparation loop; now we close the performance loop.
- This is the capstone feature that positions XfinAudio as both a preparation and performance tool.

## Scope

- **"Now Playing" panel**: current track + key / BPM / energy
- **"Next Suggestion" panel**: top 3 candidates with scores
- **Alert badge**: if a candidate breaks BPM guardrail (>3%) or key clash
- **"Load Next" button**: marks a candidate as loaded, updates set history
- **Set history timeline**: tracks played in this session, with timestamps
- **Auto-advance**: when a track is marked loaded, recalculate suggestions based on the new current track
- **Keyboard shortcuts**: Space to load next, Esc to exit Live Assistant

## Out of scope

- Auto-play or auto-mix (DJ retains full control)
- Audio output from Live Assistant (use existing AudioPreview player)
- Real-time audio analysis or DSP

## Technical approach

- Reuses existing `recommend_playlist` engine with a real-time "current track" anchor
- Thin Qt view (`LiveAssistantScreen`); all logic is deterministic scoring already tested
- Background re-scoring via `QThread` or existing async worker pattern for responsiveness
- `AudioPlayer` integration for previewing candidates directly from suggestion panel

## Complexity

High

## Risk

High (changes app architecture from prep to performance)

## User impact

Very High (product category expansion)

## Dependencies

- Option A (Audio Preview) — provides the `AudioPlayer` component
- Option B (Playlist Persistence) — provides saved playlists that can be loaded into Live Assistant

## Acceptance criteria

- [ ] LiveAssistantScreen opens as a new tab or fullscreen modal
- [ ] Current track displays with title, artist, BPM, key, energy
- [ ] Top 3 candidates displayed with transition scores
- [ ] Risky transitions show visual alert (red badge)
- [ ] "Load Next" updates current track and recalculates suggestions
- [ ] Set history shows all loaded tracks in order
- [ ] All new code covered by strict TDD
- [ ] Full test suite passes with 0 regressions
