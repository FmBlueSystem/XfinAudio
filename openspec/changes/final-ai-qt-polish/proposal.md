# Final optional-AI Qt polish

Fix three verified UI defects without new features: Live content clipping, late
Create-screen lifecycle callbacks, and misleading cancellation after local use
of completed optional-AI results. No provider, audio, dependency or persistence changes.

Success: Live remains usable at 1000×700 and 1440×1000; incomplete/deleted
widgets tolerate queued callbacks; completed results have neutral status.
Rollback: revert the affected independent slice.
Review plan: three chained commits, each below 400 changed lines: lifecycle,
completed-result status, and Live geometry. Final release gate belongs to integration.
