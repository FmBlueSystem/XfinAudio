# Native Live guidance checkpoint

Use a new isolated profile/data root and synthetic or already-authorized copied tracks only. Preserve the validated v4 source/data. No provider calls, live Serato writes or audio tag mutation are part of Live.

1. Run the Node suite with XFIN_PYTHON set; all five actual subprocess integrations must execute, not skip
2. Scan synthetic tracks and generate a genuinely ready review with the existing engine. Open Live; verify its first track, ranking scores, eligible options and empty history
3. Verify needs_review/blocked selections cannot start Live. Do not change readiness thresholds to make a fixture eligible
4. Prelisten a candidate through the existing FLAC player. Confirm prelisten does not advance the guide
5. Mark an eligible next track; current/history/revision advance once. Double clicks must not advance twice. No automatic Serato playback is implied
6. Navigate away and back; progress remains. Reopen the same review; it resumes rather than restarting. Explicit clear ends the session
7. Verify warmup/arc and protected-end behavior against the real ordered selection; no library fallback tracks are introduced
8. Change the review or start a new scan; old controls/suggestions are invalidated. Remove a copied fixture after opening; next/status must fail closed, then restore that fixture
9. Disconnect the owned test core during a pending interaction; late responses cannot revive the session. The explanatory snapshot remains unavailable and timer paused
10. Complete the exact pool. No further choices appear; the final current-track timer continues until clear. Idle app/empty Live has no timer or backend polling
11. Recheck standard scan/Prep/review/save/editor/Serato-temp workflow and muted play/pause/seek/switch. All original/copy and database sentinels stay unchanged
12. Close cleanly and verify no owned app/core processes remain. Capture the actual Live screen and report whether choices were controlled programmatically or human-operated

The pytest sharded coverage gate is infrastructure, not a relaxation of manual/native release gates. No signed distributable or live-import compatibility is established by these checks.
