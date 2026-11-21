# XfinAudio 2.9.0 Release Notes

Date: 2026-11-15

## Summary

2.9.0 is an **unreleased beta/source candidate** built on 2.8.0. It makes the
generated list safe to edit and stops the app from losing work: every change can
be undone, a compared replacement can be accepted, a track can jump to any
position, and neither the form nor the list in progress is lost on a restart.

## Editing the generated list

**Undo and redo.** The review of a generated list has **Deshacer** and
**Rehacer**. Removing, moving and replacing a track can each be undone, up to 50
steps back. Undoing a removal also lifts the ban on that track, so it can be
chosen again. A new edit clears what could be redone.

**Accept the compared replacement.** **Comparar reemplazo** used to be a preview
only. Its preview now has **Usar este reemplazo**, which swaps in exactly the
track that was compared. If the list changed since the comparison, the app asks
for a new comparison instead of applying a different track.

**Move to any position.** Each movable row has a **Posición** field and a
**Mover** button, so a track goes from position 18 to position 3 in one step.
**Subir** and **Bajar** stay. Opening, closing and manually ordered tracks stay
protected.

**Confirmation before discarding edits.** When the list has been edited,
generating again, choosing another alternative or opening a saved playlist first
asks «Vas a descartar los cambios de esta lista. ¿Continuar?». **Seguir
editando** leaves everything as it was. A list without edits is never asked
about. The alternatives stay visible after an edit.

## Nothing is lost

**The form is remembered.** After a list is generated, the app remembers the
track count, the minutes, the strategy, the intention, the name and the opening
and closing tracks, and shows them the next time it starts. A remembered track
that is no longer in the library is shown as unavailable. **Guardar controles**
for the genre and the required and excluded tracks works as before.

**The list in progress is recovered.** The list being reviewed is stored on this
computer after every change. After the app or its local service restarts, the
start screen offers **Continuar con la lista en curso**. If any of its tracks
changed in the library, the list is not recovered and the app says «La lista en
curso ya no se puede recuperar porque la biblioteca cambió».

## Compatibility

No stored data is migrated. The remembered form is an additive section of the app
settings, and the list in progress is a new file, `active_review.json`, in the
app data folder. Deleting that file only forgets the list in progress.

## Known limitations

- The undo history is not stored: after a restart the recovered list starts with
  nothing to undo.
- The recovered list uses the current preferences, not the ones in effect when
  it was generated; this only affects later comparisons and replacements.
- Undo, the replacement and the list recovery apply to the generated list, not
  yet to the editor of saved playlists.
- The new confirmation dialog and controls were verified with automated tests,
  not yet in a manual click-through.
