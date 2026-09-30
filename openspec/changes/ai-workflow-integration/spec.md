# Observable requirements

- GIVEN missing metadata WHEN repair guidance is requested THEN explain the actual
  absent fields and order repairs by declared deterministic policy, without writing tags
- GIVEN a saved set WHEN Open is activated THEN its real Editor is shown and edits
  require an explicit preview/confirm before changing the working set
- GIVEN safe local prerequisites WHEN Live is entered THEN suggestions show actual
  engine scores and constraints; missing prerequisites remain visibly unavailable
- GIVEN AI configuration errors WHEN Configure AI is selected THEN Settings opens
  at AI controls; disabled/offline AI never blocks local work
- GIVEN a running narrative WHEN its recommendation changes or request is cancelled
  THEN late results cannot attach to the new recommendation
- GIVEN the complete integrated code WHEN release gates run THEN lint, formatting,
  types, coverage, build hygiene and packaging evidence correspond to that exact SHA
