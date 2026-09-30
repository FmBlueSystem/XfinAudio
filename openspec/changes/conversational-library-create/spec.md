# Observable requirements

- R1 GIVEN existing track metadata WHEN a Library sentence specifies genre, BPM,
  Camelot key or energy THEN visible editable filters represent those constraints
  and missing metadata never becomes an invented value
- R2 GIVEN offline operation WHEN a supported sentence is submitted THEN local
  parsing works without credentials; unsupported or invalid input explains how to edit
- R3 GIVEN a Create request WHEN interpretation finishes THEN duration, style,
  role/count and existing constraints appear before any plan generation or application
- R4 GIVEN a preview WHEN Confirm is clicked THEN the deterministic local engine
  generates variants with current locks, exclusions and loudness policy preserved
- R5 GIVEN interpretation or generation WHEN Cancel/Edit or a newer request occurs
  THEN late results cannot change the active workflow; retry remains reachable
- R6 GIVEN a changed library or constraints WHEN a stale preview is confirmed THEN
  generation is blocked and the user is asked to interpret the request again
- R7 GIVEN default AI request WHEN the payload is built THEN only the request and
  genre vocabulary leave the app; optional title/genre sharing requires a visible
  per-request opt-in, and never includes audio, paths or raw metadata
- R8 GIVEN a configuration failure WHEN it is displayed THEN Configure AI is actionable
