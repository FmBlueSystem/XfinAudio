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

- GIVEN explicit optional AI action and configured consent WHEN a Library request
  returns THEN only validated editable filters may change, never track metadata
- GIVEN an Editor AI interpretation WHEN it returns THEN only a bounded local
  operation is previewed; Apply and Save remain separate explicit user actions
- GIVEN a saved-set AI query WHEN it returns THEN only IDs in the captured
  ephemeral whitelist may be used and all displayed comparisons are computed locally
- GIVEN Metadata or Live AI commentary WHEN context changes/cancels THEN stale
  commentary is rejected; neither tags nor candidate rankings can be changed
- GIVEN no consent, disabled AI or provider failure THEN local tools remain usable
  and remote recovery links directly to configuration with no silent retry
