# Observable requirements

- R1 GIVEN a narrator request WHEN the recommendation/readiness changes or the
  request is cancelled THEN old successes and failures cannot update current UI,
  including messages already queued for the UI thread; retry is possible.
- R2 GIVEN the Review screen WHEN narration runs THEN loading and Cancel are
  accessible; failure has useful guidance and Configure AI opens settings.
- R3 GIVEN computed transitions and a current Prep plan WHEN Review renders THEN
  scores, risk warnings and existing validated alternatives are explained locally;
  stale variants are not presented as comparisons to an unrelated set.
- R4 GIVEN narration facts WHEN an injected transport captures the request THEN
  only supplied metadata and computed facts appear, without filesystem paths or
  invented BPM/key/energy. Missing data remains explicitly unknown.
- R5 GIVEN an absent, blocked, stale or invalid recommendation WHEN Live is
  requested THEN it stays unavailable; no library-wide fallback can widen scope.
- R6 GIVEN a ready recommendation WHEN Live ranks/loads candidates THEN actual
  local engine transition scores determine order, previously played/excluded paths
  stay out, manual/start/end/locked controls remain respected, and risky transitions
  cannot be loaded. No network request is needed.
- R7 GIVEN one selected unprotected track WHEN Compare replacement is clicked
  THEN the local engine selects an eligible replacement and compares original
  versus proposed scores/readiness without changing the set; stale previews clear.
