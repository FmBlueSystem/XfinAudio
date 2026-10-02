# Observable requirements

1. GIVEN current settings WHEN the loudness screen opens THEN show the original enabled/target/tolerance policy, engine availability and truthful per-track states, with no audio mutation.
2. GIVEN an enabled capable engine and selected known tracks WHEN preview is requested THEN bind the exact bounded scope and current source identities, disclose automatic comment/tag replacement and backups, without writing tags.
3. GIVEN a current preview WHEN native confirmation is cancelled THEN no measurement/tag write occurs. Only main may send the backend confirmation grant. Changed source/settings/scope invalidate the preview.
4. GIVEN explicit confirmation WHEN a run executes THEN use the original FFmpeg adapter and completion service, preserve its at-most-two workers/cache semantics, update exact authorized descriptors only, and retain original bytes before changed writes.
5. GIVEN cancellation or close WHEN a commit is in progress THEN finish that commit, cancel/reap analysis children and drain the worker before exit. Late results cannot revive a replaced context.
6. GIVEN incomplete/short/unsupported/failed results THEN never display them as complete measured values. Preserve LUFS/LRA/dBTP distinctions and peak warnings.
7. GIVEN configured target/tolerance WHEN Prep uses loudness policy THEN candidate planning and generation both receive that exact original LoudnessBand.
8. All automated writes target owned copied/synthetic fixtures. Originals, live Serato and credentials/providers are untouched.
