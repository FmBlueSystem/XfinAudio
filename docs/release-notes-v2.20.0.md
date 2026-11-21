# XfinAudio 2.20.0 Release Notes

Date: 2026-11-21

## Summary

2.20.0 is an **unreleased beta/source candidate** built on 2.19.0. The preview
(«Preescuchar») can now play through a chosen audio output and a chosen pair of
its channels, so it can be heard in a DJ controller's headphones and not in the
room.

## Preview output

On the Live screen, under «Seguir a Serato», the new setting **Salida de
preescucha** has:

- **Salida**: «Salida del sistema» (the default, as before) or any audio output
  of the computer, such as the controller.
- **Canales**: the stereo pair of that output the preview is sent to («1-2»,
  «3-4», …). Left goes to the first channel, right to the second, and every
  other channel stays silent.
- **Probar**: a one-second quiet tone on exactly that output and pair, to find
  the pair by ear.

The choice is remembered. It applies to every preview of the app.

On a controller with a hardware mixer the preview arrives at the mixer channel
fed by those channels: keep that channel's fader down and its CUE on to hear it
only in the headphones.

## Safety

- If the chosen output is not connected, every «Preescuchar» is disabled and the
  setting says so. The app never moves the preview to another output by itself.
- If the output disappears during a preview, the preview stops at once.

## Security

To list and choose audio outputs the app window is now allowed to **check** two
permissions (audio devices and speaker selection), only from the app's own
page. Every permission **request** is still refused: the app cannot capture the
microphone or the camera. The audio scheme answers cross-origin reads only for
the app's own page.

## Known limitations

- Checked on macOS with a Rane FOUR (14 output channels) listed and opened while
  Serato DJ Pro was using it, and with a preview played on a virtual output and
  on the system output. **No sound was sent to the controller by the automated
  checks**: which pair reaches which mixer channel has to be found with
  «Probar».
