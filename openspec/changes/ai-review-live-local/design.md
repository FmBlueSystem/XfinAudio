# Design

Narration binds each request to the exact recommendation and readiness objects.
Worker signals carry the request identity across the queued Qt boundary and are
validated again on the controller thread. Invalidation releases UI busy state
without blocking on network cancellation. WorkerRegistry retains retired threads.
The coordinator invokes invalidate_if_context_changed during application sync.

Review displays local facts in a read-only panel and compares only a Prep plan
containing the current recommendation. Comparison is descriptive, never an apply
operation. Provider facts redact track paths even in embedded engine warnings.
Configure AI and Cancel are explicit signals wired by the integration coordinator.

Live uses a pure readiness/ranking module and a screen-local session. The initial
pool is exactly the applied recommendation, never raw scanned library records.
The local engine validates proposed remaining orders, checks readiness and scores
current-to-next transitions. Controls stay attached to the original recommendation.
The coordinator gates navigation with live_session_ready and supplies set_session.
Session identity changes clear old rows/history/timers; action handlers revalidate
paths and stop duplicate, excluded or stale selection. Local state is UI-only.
