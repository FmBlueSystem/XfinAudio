# Drain queued library labels after a pending read

Close the reproduced V17-r3 race in V17-r4 only. A newer root-count notification during a preferences metadata read must cause one subsequent read after the controller clears pending. Failed reads without new notifications must stop. Preserve dirty settings, revision, playback, focus and route.

Scope: renderer scheduling and focused regression tests. No engine, data model, security, dependency, packaging or visual redesign changes. Rollback is the bounded renderer scheduling line. One review unit, expected well under 400 changed lines including the seven artifacts; split before exceeding that budget.
