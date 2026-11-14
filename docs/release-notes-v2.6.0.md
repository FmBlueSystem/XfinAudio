# XfinAudio 2.6.0 Release Notes

Date: 2026-11-13

## Summary

2.6.0 is an **unreleased beta/source candidate**. It adds no new feature for
building sets; it hardens the desktop shell and the headless core: recovery from
a hung or stopped core, support logs, a backup before schema migrations, a
stricter check on the AI credential file, and updated dependencies.

## Core supervision

- A request to the core now has a 120 second deadline. If the core does not
  answer, the request fails, the core is stopped and the app is usable again.
  Long cancellable jobs (scan, rescan, profile completion, loudness, set
  generation, AI requests) have no deadline and are still ended by Cancel.
- A core that stops is restarted automatically, up to three times. After that
  the app asks to be restarted, as before.
- A protocol error reply without a request id is logged and ignored instead of
  stopping the core.

## Support logs

- The desktop shell writes core errors, stops, restarts, timeouts and its own
  uncaught errors to `logs/xfinaudio.log` in the app data folder (1 MiB, one
  rotated generation). Ajustes has a new **Mostrar registros** button that
  opens that folder.
- The headless core writes `core.log` in its data folder (5 MiB, three rotated
  generations) once it has accepted that folder.
- A profile analysis that fails on a track now logs the track path and the
  cause. Before, the failure left no trace.
- The logs never contain credentials or request payloads.

## Library database

- Before a schema migration, `tracks.db` is copied next to itself as
  `tracks.db.schema-v<N>.bak`. If the migration fails, the copy is restored.
  The two most recent copies are kept.
- The 5 second SQLite busy timeout is now explicit. The journal mode is
  unchanged.

## AI credential file

- A credential file that other users of the computer can read is refused before
  it is read, with the code `ai_credential_permissions`. **Action required:** if
  your credential file is not private, run `chmod 600` on it before the next AI
  request.

## Dependencies

- Electron 43.3.0 to 45.3.2 and the transitive undici 7.30.0 to 7.30.2. `npm
  audit` reports no vulnerabilities.

## Compatibility

- macOS only, unchanged. No Serato database V2 writes.
- The Electron shell and the headless core agree on version 2.6.0
  (`pyproject.toml`, `desktop-electron/package.json`, lockfiles).

## Known limitations

- The app has not been launched with Electron 45.3.2 on a real library for this
  candidate; the Electron binary starts and the automated suites pass.
- An ordinary read that takes longer than 120 seconds restarts the core, also
  while a long job is running.
- A failed profile analysis is logged but not stored: the track still looks
  like one that was never analysed.
- With a real core, the Electron integration test in
  `desktop-electron/tests/serato.integration.test.mjs` fails on this candidate
  and on 2.5.0 alike.
