# Apply progress

The original RED evidence is retained in the audit's `two-opt-score-red.log`. Recovery reproduced it on the integration tree: the unchanged-incumbent fixture made 30 calls where 16 suffice (`two-opt-recovery-red.log`).

Applied the recovered minimal cache: calculate the incumbent score at the beginning of each pass, then reuse it until a better candidate starts a new pass. The existing comparison fallback remains unchanged for other callers. Existing regression expectations were reconciled with the already-verified directional Camelot, duration-warning, and readiness contracts.

Focused and integrated verification are recorded in the verification report.
