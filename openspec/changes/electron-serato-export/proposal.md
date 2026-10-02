# Direct, confirmed Serato crate export

Restore only Serato export, directly to an explicitly selected Serato crate folder in the normal application workflow. Other export formats are outside the requested scope. Native tests use temporary _Serato_ fixtures exclusively; no authorization to write a real/live Serato destination is implied.

Preserve existing crate serialization, preview/readiness, naming, backup and readback behavior. Add immutable preview binding, name/path confinement, stale-source/destination rejection and explicit confirmation. Private staging may support safe publication, but is not the final product destination. No audio mutation, database V2 write, provider call, public push or release.

Also normalize user-facing bridge errors to clear Spanish while retaining machine codes/local technical logs, and validate source handoffs to omit dependency/cache symlinks. Chain review slices (under400 lines each): export backend/IO safety; host capability/confirmation; renderer; packaging hygiene/error UX; integration.

The explicit publication sequence and 400-line patchset rule are in `review-chain.md`; this full source snapshot is not a single proposed PR.
