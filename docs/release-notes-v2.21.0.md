# XfinAudio 2.21.0 Release Notes

Date: 2026-11-21

## Summary

2.21.0 is an **unreleased beta/source candidate** built on 2.20.0. On a Rane
FOUR the preview is sent to a **mixer channel** you choose, and the app marks
which channels Serato has a track on. It also fixes the test tone of 2.20.0.

## Choose the mixer channel (Rane FOUR)

When the preview output is a Rane FOUR, «Salida de preescucha» shows **Canal del
mezclador** instead of channel pairs, in the mixer's physical order: Canal 3,
Canal 1, Canal 2, Canal 4.

- Each channel is marked from what Serato has loaded: «Canal 4 · libre» or
  «Canal 1 · ocupado: title». A free channel is the best place for the preview.
- You choose; the app never changes the channel by itself. Picking the Rane FOUR
  as output preselects Canal 3.
- If the chosen channel is occupied the app warns that its CUE will carry both
  sounds; the preview is not blocked.
- To hear the preview only in the headphones: that channel's fader down, its
  CUE on.

Other audio outputs keep the choice by channel pair.

## Fixed

- **Probar** sent the tone to channels 1-2 whatever pair was chosen, and could
  last less than a second. It now reaches the chosen pair for one second.

## Known limitations

- The channel table (pair 1-2 is channel 1, 3-4 channel 2, 5-6 channel 3, 7-8
  channel 4) was found by ear on one Rane FOUR with Serato DJ Pro running.
- Serato reports a track as loaded, not as sounding: «ocupado» means loaded.
