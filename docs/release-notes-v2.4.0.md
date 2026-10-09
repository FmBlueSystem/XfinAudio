# XfinAudio 2.4.0 Release Notes

Date: 2026-10-08

## Summary

2.4.0 is an **unreleased beta/source candidate** built on the same cycle as 2.3.1
(AI-guided playlist improvement, legacy Qt removal) plus one new capability:
**duplicate-track avisos in DJ readiness reports**.

## Duplicate-track detection in readiness reports

Generated playlists can silently contain the same recording twice when the
library holds two entries for it (for example a clean original plus a DJ-edit
whose title metadata was damaged, so the two rows look like different songs).
Before this change the DJ only noticed after loading the crate in Serato.

The readiness pipeline now inspects every ordered playlist and adds an aviso
when two rows carry the same normalized recording identity:

- Matching uses the track title's normalized words together with artist and
  duration context, so `9 To 5 [DJ Edit]` and the truncated `To 5 (DJ Edit)`
  row are recognized as the same recording even though their titles differ.
- The aviso is advisory: it names both positions (for example rows 01 and 02),
  explains the likely cause, and lets the DJ decide — keep the edit, drop the
  duplicate, or re-tag the library row.
- No audio is read or modified and no Serato database is written; this only
  enriches the readiness report the DJ already reviews before export.

## Compatibility

- macOS only, unchanged. No Serato database V2 writes; crate exports remain
  behind the safe export/backup/validation flow.
- The Electron shell and the headless core agree on version 2.4.0
  (`pyproject.toml`, `desktop-electron/package.json`, lockfiles).

## Known limitations

- Detection is advisory metadata analysis, not audio fingerprinting: two
  genuinely different recordings with identical normalized titles, artist, and
  near-identical duration will still raise an aviso the DJ dismisses.
- A duplicated row whose artist and duration fields are also damaged may not
  be flagged.
