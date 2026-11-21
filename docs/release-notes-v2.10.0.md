# XfinAudio 2.10.0 Release Notes

Date: 2026-11-15

## Summary

2.10.0 is an **unreleased beta/source candidate** built on 2.9.0. It adds the
**list assistant**: an optional AI chat that reads the list being reviewed,
recommends improvements and answers questions about it. In this version the
assistant only reads and talks; it does not change the list.

## List assistant

On the review screen the AI panel shows **Asistente de lista**. Type a question
in **Pregunta sobre esta lista** and press **Enviar**, or start from one of the
examples: «¿Qué transiciones son las más débiles?», «¿Qué pista quitarías y por
qué?», «¿Cómo mejoro la curva de energía?».

**What it reads.** For each track: position, title, artist, genre, BPM, Camelot
key, energy and duration. For each transition: its score, explanations and
warnings. Also the readiness status with its blockers and warnings, and which
positions are protected. It never receives a file path or an internal track
identifier. **Ver lo que se envía** shows the exact request before it is sent.

**A conversation, not single questions.** The assistant remembers the
conversation while the list is being worked on. When the list is edited between
questions (remove, move, replace, undo), the assistant reads it again and the
reply starts with «El asistente volvió a leer la lista.». **Nueva conversación**
starts over.

**Answers.** In Spanish, at most 250 words, naming tracks by position and title,
with concrete suggestions: which track to remove, where to move one, or which to
replace and why.

## Privacy and consent

- The assistant is part of the optional AI: it works only when AI is enabled and
  a credential is selected, and it uses the same provider as the other AI
  features.
- The confirmation dialog appears on the **first message of a conversation**.
  Later messages of the same conversation send the same kind of data and are
  not asked again. A new conversation, a new or discarded list, or a change of
  the AI settings or credential asks again.
- The conversation is kept in memory only. It is never written to disk and is
  forgotten when the app or its local service restarts.
- A failed or cancelled message is not added to the conversation, and the typed
  text stays in the box.

## Compatibility

No stored data changes. The existing AI commentary of the review works as before.

## Known limitations

- The assistant only advises. Applying its suggestions (remove, move, replace)
  from the chat is planned for the next version; for now use the review controls.
- It works on the generated list, not yet on the editor of saved playlists.
- A list of more than 100 tracks is refused.
- Each answer is one request of up to 120 seconds; there is no streaming.
- The quality of the advice depends on the provider model. It was verified with
  a simulated provider in automated tests, not with real provider answers or a
  manual click-through.
