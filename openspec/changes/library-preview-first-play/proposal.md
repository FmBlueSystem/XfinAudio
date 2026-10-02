# Preserve the first preview interaction

Fix the first Library Play after direct table population without rebuilding active
items. Scope: playback highlighting and fake-player regressions. No real audio,
Qt internals, accessibility bypass, or claim that this resolves a native AX crash.
Rollback: revert this isolated slice. Review budget: at most 400 changed lines.
