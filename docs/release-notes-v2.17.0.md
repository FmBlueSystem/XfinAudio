# XfinAudio 2.17.0 Release Notes

Date: 2026-11-20

## Summary

2.17.0 is an **unreleased beta/source candidate** built on 2.16.0. A saved
playlist can now be edited like a list that was just generated, with the same
controls and the list assistant, and saved back.

## A saved playlist is a list in progress

Opening a saved playlist from **Listas guardadas** shows it on the review screen
as **PLAYLIST GUARDADA**, with everything a generated list has: the **Mezcla**
column, **Qué revisar**, **Deshacer** and **Rehacer**, compare and replace,
move, extend, and the bot button of **Asistente de lista**, which can search the
library and propose changes for it.

- **Guardar cambios en la playlist** appears while the list has changes that are
  not saved, and writes them to the same playlist: «Playlist guardada: name».
- **Guardar como playlist nueva** keeps the original and saves a copy.
- If the playlist was changed somewhere else since it was opened, saving is
  refused: «La playlist cambió en otro lugar. Ábrela de nuevo para no perder
  cambios.»
- The first and the last track of a saved playlist are not protected.
- The list is recovered after a restart, still tied to its playlist.
- Opening a saved playlist while another list has unsaved changes asks before
  discarding them.

A playlist with a track that is no longer in the library, or with fewer than two
tracks, opens read-only as before.

## Texts

One change is now singular: «Se aplicó 1 cambio.» and «Se deshizo 1 cambio.».

## Compatibility

No stored data is migrated. The recovery file of the list in progress has a new
version that also holds the playlist it came from; a file written by an earlier
version is still read.

## Known limitations

- A saved playlist that holds the same track twice can be edited, but it cannot
  be reordered.
- The short-list notice and the alternatives do not apply to a saved playlist.
- Checked on screen with one test playlist: open, a change proposed and applied
  by the assistant, and saving back.
