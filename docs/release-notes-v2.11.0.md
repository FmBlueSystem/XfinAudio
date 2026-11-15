# XfinAudio 2.11.0 Release Notes

Date: 2026-11-15

## Summary

2.11.0 is an **unreleased beta/source candidate** built on 2.10.0. The list
assistant can now **propose changes** to the list being reviewed, and each one
is applied with one click. The assistant never changes the list by itself.

## Proposed changes

When a reply of **Asistente de lista** includes changes, they appear under
**Cambios propuestos**, one card each, with the reason:

- **Reemplazar 7. Title por Other title** — the track leaves the list and the
  track the engine proposes takes its place. The card shows which track comes
  in. This is also how the assistant "removes" a track: a generated list keeps
  its length, so a removed track is always replaced.
- **Mover 12. Title a la posición 4** — the track moves there.

Press **Aplicar** on a card to make that change. The review updates as after a
manual edit, the remaining cards are kept with their new positions, and the app
says «Cambio aplicado. Puedes deshacerlo con Deshacer.». **Deshacer** reverts it
like any other edit.

## What keeps this safe

- A reply can propose at most five changes, only of those two kinds.
- The app checks every proposed change before showing it. Changes that point to
  a position that does not exist, to a protected track (opening, closing or
  required), or that are malformed are discarded, and the panel says how many.
- The replacement is always chosen by the app's engine, never by the AI.
- If the list changed and a card no longer applies, pressing **Aplicar** changes
  nothing and the cards are cleared; ask the assistant again.
- Applying a change does not contact the AI provider.
- The assistant cannot save, export or delete anything.

## Compatibility

No stored data changes. Pending proposed changes live in memory with the
conversation and are forgotten with it.

## Known limitations

- The AI does not choose among several replacement candidates; it proposes which
  track to replace and the engine picks the replacement.
- There is no "apply all"; changes are applied one at a time.
- Proposed changes work on the generated list, not yet on the editor of saved
  playlists.
- Verified with a simulated provider in automated tests, including hostile
  answers; not yet with real provider answers or a manual click-through.
