# Requirements

- R1: GIVEN a dirty library WHEN a scan succeeds THEN every desktop consumer sees
  the cleared flag and the change banner stays hidden after later renders.
- R2: GIVEN a folder vanished or watching is unavailable WHEN scan completion
  attempts to start/resume watching THEN scan state still finishes and the user
  receives a recoverable warning; no false active watch is reported.
- R3: GIVEN scan, recommendation, or AI work is running WHEN close is requested
  THEN cancellation is requested, the event loop stays responsive, ownership is
  retained, and close finishes only when all workers have stopped.
- R4: GIVEN a worker was replaced or analysis was canceled earlier WHEN close is
  requested THEN retired workers are also drained without forced termination.
- R5: GIVEN a scan committed records before cancellation WHEN close completes
  THEN committed records remain readable.
