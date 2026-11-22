# XfinAudio 2.27.0 Release Notes

Date: 2026-11-22

## Summary

2.27.0 is an **unreleased beta/source candidate** built on 2.26.0. **The list
assistant no longer looks stuck**, **an approved turn is never asked again**,
**its answers are readable more often**, and **the model is chosen in the
settings** from a fixed list of Nan models while the endpoint stays pinned.

## A turn shows what it is doing and can be cancelled

A list-assistant turn could look frozen for minutes: the chat showed no time, no
phase and no way out, and only the core restart ended it. Now, while a turn runs,
the chat shows the elapsed seconds and the phase it is in — preparing the
request, waiting for the system confirmation dialog, waiting for the AI, applying
the proposed changes — and offers **Cancelar**.

Cancelling ends the turn, frees the app and changes nothing in the list: a late
answer is discarded, and the question stays in the field so the DJ can send it
again.

## A slow provider call ends with a clear message

Each provider call now has a bound owned by the app itself, so a socket that
never answers ends the turn with the Spanish message «El proveedor no respondió a
tiempo…» instead of a silent hang or a core restart. A turn never waits longer
than that bound per call it makes, and the local service keeps running.

This is the `ai_timeout` end: nothing is applied, the list is untouched, and the
turn can be retried.

## Errors that used to disappear are reported

The chat now says in Spanish what was lost before: a batch that applied nothing,
a failed save of the «No volver a preguntar en cada consulta» preference, a
refused apply, and a proposed change that is no longer available. None of these
texts imply that something was applied.

## An approved turn runs, and does not ask again

Ticking the dialog's **do not ask again** option while approving a turn saved the
preference immediately, which revoked the prepared preview and reset the
conversation: the turn the DJ had just approved asked again. The preference is
now stored **after** the approved turn runs, so the save never revokes the turn it
accompanies.

Only granting the switch (off → on) keeps a pending turn. Taking it away revokes
the pending turn, so a continuation is never sent with automatic authorization
off and no dialog.

## One stale card no longer clears the others

When one proposed card became stale, the whole answer was cleared. Now only that
card is refreshed or reported and the remaining cards stay applicable against the
list as it is. **Aplicar todo** applies the steps in the shown order and includes
a proposed alternative, which is chosen through the screen's variant path and
goes last because it replaces the whole list.

## The model sees what was already applied

The next turn now receives, besides the changes applied since the previous
answer, the proposals of that conversation that are already in the list, so the
model does not propose them again and does not claim it cannot see them.

The instructions also state that a period action applies only when it replaces at
least one track outside the period, so that action is proposed only when it does
something.

## Readable answers: JSON, one repair, examples

Every list-assistant turn now asks the provider for a JSON answer at temperature
0.2, so the same request produces a steadier format. When the provider rejects
the JSON format field, the request is repeated once without it.

When the answer has no parseable JSON (prose only or cut JSON) while a change was
asked for, the turn asks the model once to answer again in the required format
and reads that answer. A second failure keeps the received text with a short
notice and proposes no change. A turn never makes more than four calls, and the
instructions now include three short example answers.

With `XFINAUDIO_CHAT_LOG=1`, the chat log also records failed, cancelled and
repaired turns and every dropped change with its reason, so quality can be
measured.

## The model is chosen in the AI settings

The AI panel offers **Modelo de Nan Builders**: **DeepSeek V4 Flash**, the
default, **GLM 5.3 Flash** and **Qwen 3.6**. Only the model id varies; the
recipient stays pinned to `https://api.nan.builders/v1/chat/completions`, and the
panel offers no destination field.

The choice is persisted with **Guardar ajustes de IA**, survives restarts and is
used by every assistant request. The disclosure shown before a request names the
model that request will carry, and changing the model revokes a prepared preview
and starts a new conversation, so a turn is never applied to the wrong model
silently. An unknown model is refused instead of sent.

## What does not change

- AI stays off by default, the credential is still read only after the model gate,
  and no panel offers a destination or a free-text model name.
- Metadata scanning stays read-only, no audio file is mutated outside loudness
  tag writing, and no live Serato database V2 file is written.
- Preparing a turn still checks only the tracks of the list in progress and the
  tracks the request names, and staleness protections are unchanged.
- Saving, exporting to Serato and editing a list behave as in 2.26.0.

## Known limitations

- Cancelling while the turn is still preparing does not cut the local preparation
  job: the turn is reported as cancelled once preparation returns.
- **GLM 5.3 Flash** and **Qwen 3.6** were not exercised against the real provider
  by the agent; the verification uses synthetic credentials and injected
  transports, so it does not certify a real NaN account.
- Quieter quality regressions still depend on the optional chat log; measuring
  them requires setting `XFINAUDIO_CHAT_LOG=1` before the session.
