# XfinAudio 2.5.0 Release Notes

Date: 2026-10-08

## Summary

2.5.0 is an **unreleased beta/source candidate** built on the same cycle as 2.3.2
(AI-guided playlist improvement, legacy Qt removal) plus one new capability:
**Serato destination auto-discovery**.

## Serato destination auto-discovery

Exporting a crate no longer requires choosing a folder. The app now looks for a
usable `_Serato_` destination on its own:

- Each scanned library root is checked for `<root>/_Serato_` with a `Subcrates/`
  folder — the common layout where the library and Serato share a volume.
- As a fallback, `~/Music/_Serato_` is suggested only when it lives on the same
  source volume as the scanned library; `serato.preview` refuses cross-volume
  destinations, so a suggestion that could not commit is never offered.
- The suggested folder travels through the same validated registration as a
  hand-picked one (canonical path, `Subcrates/` check, lineage). If no usable
  destination is found — or discovery fails — the native folder picker opens
  exactly as before. The picker remains the authority; discovery is convenience.

Crate naming is unchanged: generated crates still nest under the `XfinAudio`
root crate (for example `XfinAudio%%Harmonic Journey%%…`), so exports keep
landing inside the `XfinAudio` crate in Serato.

## Compatibility

- macOS only, unchanged. No Serato database V2 writes; crate exports remain
  behind the safe export/backup/validation flow.
- The Electron shell and the headless core agree on version 2.5.0
  (`pyproject.toml`, `desktop-electron/package.json`, lockfiles).

## Known limitations

- A library on an external volume with Serato configured only under `~/Music`
  gets no suggestion (volume rule) and uses the picker.
- A `_Serato_` folder relocated through a symlink can yield a suggestion that
  preview then blocks on the volume rule; retrying after removing the symlink
  self-heals, and the picker never becomes unreachable.
