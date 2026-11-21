# XfinAudio 2.13.0 Release Notes

Date: 2026-11-15

## Summary

2.13.0 is an **unreleased beta/source candidate** built on 2.12.0. When a list
comes out shorter than requested, the app now says so and offers the fixes; a
generated list can be **extended**; and the list assistant knows why a list is
short and can propose extending it or using another alternative.

## A list shorter than requested

The review shows «Salieron 4 de 20 pistas.» and, when a genre was used, that the
genre and the mixing rules left few candidates. Three fixes, as buttons:

- **Ampliar a 20 pistas** — adds tracks from the library (see below).
- **Usar la alternativa de 20 pistas** — when another alternative of the same
  generation has more tracks.
- **Generar sin género** — clears the genre and generates again.

## Extending a list

Extending adds tracks until the list has the requested number or no track is
left that mixes with it. The engine first uses tracks of the chosen genre and
only then the rest of the library, and says how many came from other genres.
Each new track is placed where it mixes best, so new tracks are spread through
the list and a good existing transition is not broken for a worse one. The
tracks already in the list keep their order, protected tracks keep their place,
removed and excluded tracks do not come back, and other versions of a song that
is already in the list are not added. The whole extension is one step for
**Deshacer**.

## The assistant

**Asistente de lista** is now told how many tracks were requested, the engine
warnings and the other alternatives with their track count and score. It can
propose two more changes, each applied with **Aplicar** like the others:
«Ampliar la lista a 20 pistas» and «Usar la alternativa exploratoria (20
pistas)». Choosing an alternative starts a new conversation.

## Diagnostics

Starting the app with `XFINAUDIO_CHAT_LOG=1` writes each assistant message, the
provider answer and every applied or discarded change to `logs/list-chat.log` in
the app data folder. It is off by default; without it the conversation is never
written to disk.

## Compatibility

No stored data changes.

## Known limitations

- Extending a list can take several seconds on a large library.
- The assistant still cannot choose which tracks are added; the engine does.
- An extended list tends to stay in the keys of the tracks it already had.
- The same-song rule applies to extending; generation still relies on the
  engine's own duplicate rule.
- Extending and the notice apply to the generated list, not to the editor of
  saved playlists.
- Verified with automated tests and one run on a copy of a real library; the
  new buttons were not yet clicked through by hand.
