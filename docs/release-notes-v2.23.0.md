# XfinAudio 2.23.0 Release Notes

Date: 2026-11-22

## Summary

2.23.0 is an **unreleased beta/source candidate** built on 2.22.0. The preview
output can now be **calibrated for any DJ controller**, and the preview setup is
really kept between sessions.

## Calibrate any controller

In «Salida de preescucha», with any output other than the system one, **Calibrar
canales** walks through every stereo pair of the device: it plays the test tone
on the pair and asks «¿Dónde sonó?» — Auriculares, Sala, Canal 1 to Canal 4, or
No sonó.

- Afterwards the app offers destinations by name instead of pairs: «Auriculares»
  first, then the mixer channels, each marked free or occupied from Serato.
- Pairs that sound in the room, or nowhere, are **never offered** for the
  preview.
- The calibration is kept per device. The Rane FOUR keeps its built-in channel
  table unless it is calibrated. **Borrar calibración** returns to the pairs.
- The wizard warns to lower the room volume first: the tone plays on every
  output, the room included. No preview can start while it is open.

## Fixed: the preview setup was lost on restart

Since 2.20.0 the chosen output and pair were kept only until the app was closed
(the notes said they were remembered; they were not). The output, the pair and
the calibrations are now kept by the app itself in its data folder and are
there after a restart.

## Security

Two new actions let the app window read and save that setup. The saved value has
a strict shape and a bounded size, goes to one fixed private file, and no path
is ever returned to the window. Verified independently.

## Known limitations

- The wizard was exercised on screen on a virtual (inaudible) output. It was not
  run on a real controller by these checks.
