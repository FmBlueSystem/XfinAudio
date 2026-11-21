# XfinAudio 2.18.0 Release Notes

Date: 2026-11-21

## Summary

2.18.0 is an **unreleased beta/source candidate** built on 2.17.0. **Live now
follows Serato**: the app reads which track is loaded on each deck in Serato DJ
and suggests what to play next from the whole library.

## Live follows Serato

Open **Live** from the navigation; it no longer needs a generated list. With
**Seguir lo que suena en Serato** on (the default):

- **Sonando en Serato** shows one line per deck: «Deck 2: Title — Artist · 127
  BPM · 4B». The track loaded most recently is marked **Actual**.
- **Qué poner después** lists up to ten tracks of the library that mix best with
  the current track, by tempo, key and energy, each with its transition
  («Buena · 87 %») and **Preescuchar**. Tracks already played in the Serato
  session, and other versions of them, are left out.
- The screen asks Serato's history every 3 seconds and updates by itself when a
  deck changes.

The manual Live guide of a generated list is still available below.

## How it reads Serato

Serato DJ 5 keeps its history in a database in its own library folder. XfinAudio
opens it **read-only** and reads two tables. It never writes to it, never
creates a file next to it, never controls Serato, and one read is cut off after
one second. If the history cannot be found or read, the screen says so and
retries by itself.

## What to know

- Serato records a track when it is **loaded on a deck**, not when its fader is
  up. The app cannot hear the audio: «Actual» is the most recently loaded deck.
- A track that plays in Serato but is not in the XfinAudio library is shown with
  Serato's own title and artist, and gives no suggestions.
- Suggestions come from the 200 library tracks closest in tempo to the current
  one.

## Compatibility

No stored data changes. Serato DJ versions that keep their history in the old
binary session files are not read.

## Known limitations

- If the same file name exists in two folders, or the same path on two drives,
  the app takes the one whose BPM is closest to Serato's.
- Checked on macOS with Serato DJ Pro 5.1 running; the Windows path was not
  exercised.
