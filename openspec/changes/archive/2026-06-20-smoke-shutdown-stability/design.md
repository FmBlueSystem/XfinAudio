# Design: Smoke shutdown stability

## Approach

Keep the fix in the desktop application startup boundary. Smoke mode is a packaging/runtime launch concern, not domain logic.

The app should avoid constructing or starting background spectral completion workers when smoke mode is active. The normal application startup path must remain unchanged when smoke mode is disabled.

## Safety

- No DSP behavior changes.
- No audio mutation.
- No Serato DB V2 writes.
- No export format changes.
- No dependency changes.
