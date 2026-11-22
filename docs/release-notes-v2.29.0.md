# XfinAudio 2.29.0 Release Notes

Date: 2026-11-22

## Summary

2.29.0 is an **unreleased beta/source candidate** built on 2.28.0. **The list
assistant's answers are readable more often**, its failed and repaired turns can
be measured, and **the model is chosen in the AI settings** from a fixed list of
Nan models while the endpoint stays pinned.

## Readable answers: one JSON object, one repair, three examples

Every list-assistant turn now asks the provider for a JSON answer at temperature
0.2, so the same request produces a steadier format. A provider that rejects that
format field with HTTP 400 naming it is asked once more without it, so one
rejected request still ends with an answer instead of a failed turn.

When the answer carries no readable JSON — prose only or JSON cut short — while
the DJ asked for a change, the turn asks the model once to answer again in the
required format. A second failure keeps the text the model wrote with a short
notice and proposes no change, so an unreadable answer is never a silent empty
turn. A whole turn never spends more than four provider calls, repairs included,
and each of those calls keeps its own bounded wait from 2.27.0.

The instructions now show three short example answers — a replacement, a move and
a reply with no changes — so the required shape is shown, not only described.

## The chat log records cancelled and repaired turns

Before this version, 7 of the 25 turns in the DJ's own log ended with no
applicable action: the answer was not JSON at all, or it was cut short. Nothing
recorded why, so the quality could not be measured.

With `XFINAUDIO_CHAT_LOG=1` the log now also records a cancelled turn and the
phase it ended in (before sending, during the call, after it, before publishing),
the answers that had to be asked again, and every dropped change with its reason.
Measuring quality still requires that switch before the session.

## The model is chosen in the AI settings

The AI panel offers **Modelo de Nan Builders**: **DeepSeek V4 Flash**, the
default, **GLM 5.3 Flash** and **Qwen 3.6**. Only the model id varies; the
recipient stays pinned to `https://api.nan.builders/v1/chat/completions`, and the
panel offers no destination field and no free-text model name.

The id is checked in three places — the stored settings, the app before any
credential is read, and the desktop shell's own request allowlist — so a model
outside that list is refused instead of sent, and a settings object built without
validation cannot carry one to the provider.

The choice is persisted with **Guardar ajustes de IA**, survives a restart and is
used by every assistant request. The confirmation shown before a request now
names the model that request will carry, changing the model revokes a prepared
preview and starts a new conversation, and the model saved in the file stays in
force until the new one is saved.

## What does not change

- AI stays off by default, the credential is still read only after the model gate,
  and no panel offers a destination.
- Preparing, confirming and applying a turn, the phase and seconds line,
  **Cancelar** and the per-call timeout behave as in 2.27.0.
- An approved turn is still applied without asking again, only granting the
  approval switch keeps a pending turn, one stale card no longer clears the
  others, and any other settings save still starts a new conversation (2.28.0).
- Metadata scanning stays read-only, no audio file is mutated outside loudness tag
  writing, and no live Serato database V2 file is written.

## Known limitations

- **GLM 5.3 Flash** and **Qwen 3.6** were not exercised against the real provider
  by the agent; the verification uses synthetic credentials and injected
  transports, so it does not certify a real NaN account for either model.
- Cancelling while the turn is still preparing does not cut the local preparation
  job: the turn is reported as cancelled once that preparation returns, as in
  2.27.0.
- Quieter quality regressions still depend on the optional chat log; measuring
  them requires setting `XFINAUDIO_CHAT_LOG=1` before the session.
