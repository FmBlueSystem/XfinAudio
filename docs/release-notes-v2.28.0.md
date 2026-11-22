# XfinAudio 2.28.0 Release Notes

Date: 2026-11-22

## Summary

2.28.0 is an **unreleased beta/source candidate** built on 2.27.0. **An approved
list assistant turn is applied without asking again**: the system dialog's «No
volver a preguntar en cada consulta» no longer invalidates the turn it
accompanies, and the errors and proposals around an approved turn behave the way
the DJ expects.

## An approved turn is applied without asking again

On 2026-11-21 the DJ approved the same assistant turn four times before a change
was applied. Ticking «No volver a preguntar en cada consulta» in the confirmation
dialog saved the preference while the approved turn was still pending; that save
looked like a configuration change, so the prepared turn went stale, the
conversation was reset, and the assistant asked the same question again.

The preference is now stored **after** the turn it approved has run, so the save
can never revoke that turn. The approved turn runs and its changes are applied;
the switch is turned on once it finishes.

## Only granting the approval switch keeps a pending turn

Turning the approval switch **on** while a turn is pending keeps that turn: only
the switch changed and nothing the turn is sent with, so the retained preview and
answers stay as fresh as they were and the turn is sent as approved.

Taking the switch **away** does the opposite, because withdrawing consent is a
real configuration change: the pending preview is revoked and the conversation
resets, so the next turn is disclosed and confirmed again.

The deferred save does only that one thing. It reads the settings immediately
before writing, keeps the enabled state and the chosen model it finds, and stores
nothing at all when the AI was disabled during the turn — turning the AI off mid
turn is never silently undone. When the preference cannot be stored, the chat
says so in Spanish instead of hiding it.

## One stale card no longer clears the whole answer

When one proposed card could no longer be applied, every card of the answer was
cleared. Now only that card leaves the list, with the reason reported, and the
rest is re-read from the app so the remaining cards stay applicable against the
list as it is now.

**Aplicar todo** applies the remaining steps in the order shown, and a proposed
alternative is no longer skipped: it is chosen through the screen's own variant
route, at the end, because it replaces the whole list.

## The model sees what it already proposed and what a period action can do

A later turn now also receives the proposals of this conversation that are
already in the list, so the assistant stops proposing them again and stops
answering that it cannot see them. A period change is proposed only when it
replaces at least one track that is outside the period, so asking to keep the
list inside a range it already satisfies no longer produces an action that
applies nothing.

The line a single-track move is reported with now names both ends of the move —
«Mover la posición N a la posición M» — instead of falling back to the wider
reorder line.

## What does not change

- Preparing, confirming and applying a turn, the phase and seconds line, **Cancelar**
  and the per-call timeout behave as in 2.27.0.
- The list conversation still asks its own consent once per conversation, keeps
  the staleness protections, and stays in memory only.
- **Any other AI settings save still starts a new conversation** and discloses it
  again; the approval switch going off does, and the same applies to a save
  through **Guardar ajustes de IA**, a different credential file, **Nueva
  conversación**, discarding the generated list and restarting the app.
- The endpoint, the model and the disclosure are unchanged, AI remains off by
  default, and no audio file is written.

## Known limitations

- The approval switch is stored best effort once the approved turn has run. If the
  app cannot read the settings or the store refuses that one write, the switch
  stays as it was, the chat reports it, and **Ajustes** remains the reliable way
  to set it.
- Cancelling while the request is being prepared still lets that local
  preparation finish before the turn ends as cancelled, as in 2.27.0.
