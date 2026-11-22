# XfinAudio 2.36.0 Release Notes

Date: 2026-11-22

## Summary

2.36.0 is an **unreleased beta/source candidate** built on 2.35.0. It is the
first part of the profiles work, and it removes a **dead end**: while the library
reports **«Cambios detectados»** the profiles area now offers one action —
**«Reescanear y completar perfiles»** — that rescans the library and then
completes the profiles, so pending analysis is never blocked with no way
forward. The status also says **what is pending per analysis** and, once a run
has measured some tracks, **how long it has left** in Spanish.

## The dead end it removes

Completing profiles was refused while the library was stale, and the library is
stale whenever the watcher reports detected changes — including after a profile
run of its own. The only thing that cleared the stale state was a rescan, and the
rescan was offered elsewhere on the screen, so the profiles area could show a
disabled button for as long as the changes were not scanned.

The real case that produced this version: on 2026-11-22 the DJ's library held
**10 391 tracks** with **453 spectral**, **0 danceability** and **0 edge**
profiles, so the status reported all 10 391 tracks pending. Profile completion
had **never** run, because the stale state kept blocking it.

## One action instead of a blocked button

When the library is stale the profiles area shows **«Reescanear y completar
perfiles»**. It starts the same rescan the rest of the app already uses, and the
existing chain of that rescan runs the profile step afterwards as step **2 of 2**
of one job, so the DJ sees a single operation from start to end. The action
follows the same rules as everything else: it is disabled while another job is
running and while profile analysis is already in progress, and it needs at least
one registered music folder.

There is no second rescan implementation: the button hands over to the rescan
that already exists.

## The stale state comes from the rescan's own result

A rescan is exactly what clears «Cambios detectados», and it also reruns the
watcher, so its own events could have arrived mid-run and cancelled the profile
job it had just started. Staleness is therefore no longer read from the last
library status the watcher published: it now comes from **the rescan's result**.

- A rescan that **completes** is treated as having cleared the stale state, so
  the chained profile step runs and cannot be cancelled by the rescan's own
  events.
- A rescan that is **cancelled** changed nothing, so it keeps whatever the
  watcher still reports and the profiles area keeps offering the action.

## The manual path still works

When the library is **not** stale, **«Completar / reintentar perfiles»** behaves
exactly as before: it completes the profiles without rescanning, and it stays
disabled while analysis is running, while the library is stale or when every
track is complete. The automatic profile step that follows an ordinary scan is
unchanged.

## The status says what is pending

The profiles summary now names the pending work **per analysis**:

```text
Perfiles pendientes: 453 de 10391 pistas completas · 9938 pendientes · 0 fallidas.
Pendientes por análisis: espectral 9938 · bailabilidad 10391 · bordes 10391.
```

The per-analysis counts are not a guess: readiness and pending are the two halves
of the same total, and a summary where a stage's ready and pending counts do not
add up to the library total — or where a stage claims fewer ready tracks than the
library as a whole — is rejected as invalid instead of displayed.

## A measured remaining time

Once a run has finished analysing some tracks, the status adds an estimate in
Spanish, such as **«Faltan unas 3 h 20 min»**. The wording follows the measured
magnitude: «Falta menos de un minuto», «Faltan unos 12 min», «Falta 1 h»,
«Faltan unas 3 h 20 min».

The estimate is a **measurement, not a constant**: the core times each analysis
as it commits tracks and divides that time by the tracks it analysed, then
multiplies the per-track time by what is still pending. An analysis that has not
run yet is estimated with the average already measured, so a fresh library still
gets an estimate after its first stage. Nothing is claimed before anything has
been measured: with no measurement the status shows no time at all.

Only a batch that **fully committed** feeds the measurement, so a cancelled run
does not record the time of decodes it abandoned. While a run is in progress the
estimate travels with its progress events, so the number moves as the run
advances; the stored status keeps the last estimate that run published.

## What does not change

- **No profile value changes**: spectral, danceability and edge analysis, their
  windows, sample rates and tolerances are untouched. Completion still decodes
  each analysis separately, so this version does not make a run faster.
- **The profiles stay read-only**: metadata remains available during analysis, no
  audio file is mutated outside loudness tag writing, and no live Serato
  database V2 file is written.
- **A run stays divisible**: it can be cancelled and resumed, and each track
  commits on its own, so nothing already analysed is lost.

## Known limitations

- The remaining time is measured **in this process only**. After a cancelled run
  or a fresh start nothing has been measured yet, so the status shows the pending
  counts without a time until the new run commits its first batch.
- A cancelled run keeps what it already committed, but not the measurement of the
  batch it interrupted.
- The estimate on the real library is measured in **hours**, and the app is busy
  while it runs: completing about **10 400 tracks** takes roughly **3 to 4 hours**
  with the two workers it uses, and **danceability** dominates that time.
- The 2.36.0 candidate is source-only: no installer, updater or binary
  redistribution is claimed by this version.
