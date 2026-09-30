# Apply progress
- RED: dedicated synthetic regression target produced 25 failures and 12 passes before production edits (2026-09-30).
- GREEN: shared finite-positive predicate now validates rounded tag candidates, rejects malformed persisted tempos before scoring, and blocks metadata/continuity readiness independently of stale completeness flags.
- REFACTOR: both tag candidate paths retain fallback; scoring/readiness share validity without changing stored models. Missing tempo keeps existing scoring behavior. No arbitrary tempo maximum added.
- VERIFY: 185 focused tests pass; changed-file lint, format and type checks pass. Final integration gate remains owned by integration lead.
