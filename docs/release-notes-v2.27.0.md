# XfinAudio 2.27.0 Release Notes

Date: 2026-11-22

## Summary

2.27.0 is an **unreleased beta/source candidate** built on 2.26.0. **A list
assistant turn now shows what it is doing and how long it has taken, can be
cancelled, and never waits forever on one provider call**; the errors it used to
hide are shown in the chat.

## The turn shows its phase and its time, and offers Cancelar

A chat turn gave no sign of progress: the same quiet line stayed on screen while
the request was prepared, while the system confirmation dialog was open, and
while the provider answered for up to two minutes, so the assistant looked stuck
and there was no way out of it.

While a turn runs, the chat now names the phase it is in — preparing the request,
waiting for the system confirmation dialog, waiting for the AI, applying the
proposed changes — next to the elapsed seconds, which are redrawn every second.

**Cancelar** is offered for exactly the running turn. Cancelling ends the turn,
frees the app, and leaves the list untouched: nothing is applied, the question
stays in the field so it can be asked again, and an answer that arrives after the
cancellation is discarded.

## A provider call ends at its own budget

Each provider call has a bounded wait (120 s in the chat, less for the other
actions), owned by the app rather than trusted to the transport, so a hung
socket or a provider that drips bytes is cut instead of holding the turn.

When the budget expires the turn ends with the code `ai_timeout` and a Spanish
message that says the provider did not answer in time and that nothing was
applied. The local service is not restarted: the app stays available and the
question can be sent again. A turn never waits more than that bound for each call
it makes, including the second call of a search.

## What used to fail in silence is now said in the chat

Three failures were dropped without a word: an automatic batch that applied none
of the proposed changes, a proposed card that could no longer be applied (or a
refused apply), and a system dialog that could not store the «No volver a
preguntar en cada consulta» preference. Each one now appears as its own line in
the chat, in Spanish, and a line never claims that something was applied when it
was not.

## What does not change

- Approving a turn, applying proposed cards, applying all of them, undoing a
  batch and the review screen behave as in 2.26.0.
- The assistant still prepares a turn from the list in progress and the tracks
  the request names, keeps the staleness protections, and reads the library the
  same number of times.
- Every other long operation keeps its own progress line and its own
  cancellation.
- AI remains off by default, the endpoint and the model are unchanged, and no
  audio file is written.

## Known limitations

- Cancelling while the request is being prepared does not stop that local
  preparation: the turn ends as cancelled once the preparation returns, and
  nothing is sent to the provider before that.
