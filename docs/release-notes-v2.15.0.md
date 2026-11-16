# XfinAudio 2.15.0 Release Notes

Date: 2026-11-15

## Summary

2.15.0 is an **unreleased beta/source candidate** built on 2.14.0. The list
assistant becomes a **bot button with a floating chat window**, and it gets the
tools to change the list: remove, add a track it found, replace with a track it
found, reorder, undo, and a search of the library.

## Bot button and floating window

On the review screen a round bot button sits at the bottom right. It shows how
many proposed changes are waiting. It opens **Asistente de lista** in a window
that floats over the list without moving it; the list behind stays usable.
**Minimizar** or the Escape key hides the window and keeps the conversation.
The other AI functions stay in the AI panel.

## New tools

The assistant still never changes the list by itself: each change is a card with
**Aplicar**, and **Aplicar todo** applies them in order.

| Card | What it does |
|---|---|
| Quitar 5. Title | Takes the track out without a replacement; the list gets shorter |
| Agregar Title en la posición 14 | Adds a track the assistant found in the library |
| Reemplazar 9. Title por Other | Swaps in a track the assistant found |
| Reordenar la lista (15 pistas cambian de lugar) | Applies a new order; protected tracks stay |
| Deshacer el último cambio | Reverts the last change; proposed alone |

Every change is one step for **Deshacer**, keeps protected tracks, and refuses a
track whose file changed on disk.

## Library search

To choose tracks, the assistant can search the library once per message: up to
two searches by text, genre, BPM range or key, up to 20 results each. Only
tracks with complete metadata that are not in the list are found. **The title,
artist, genre, BPM, key, energy and duration of the tracks found are sent to the
AI provider**; never a file path or an internal identifier. The confirmation of
the first message says so. A message that searches takes two requests to the
provider, so it takes longer.

## Checked with the real provider

On a copy of a real library, with a 20-track list: the assistant searched for an
artist near a tempo and proposed adding one track where it mixed best; searched
again and proposed a swap that kept the key of its neighbours; proposed a
removal, a full reorder by tempo and an undo. All five were applied and the
undo restored the previous list. Messages took 14 to 43 seconds; applying a
change about 3 seconds.

Two defects found in that run are fixed here: answers with line breaks were shown
as raw text with no changes, and the searches the provider writes were ignored.

## Compatibility

No stored data changes. The conversation, the search references and the pending
changes live in memory only.

## Known limitations

- One search round per message.
- A reorder can lower the mix score; the review shows it and **Deshacer**
  reverts it.
- The new edits are available through the assistant only, not as manual
  controls, and only on the generated list.
- The floating window and the new cards were verified with automated tests; they
  were not yet clicked through by hand.
