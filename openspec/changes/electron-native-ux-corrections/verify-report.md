# Verification

Strict RED→GREEN:69-test baseline had10 intended failures; final build+77 affected tests passed,0 failed/cancelled/skipped/todo. Logs under `/workspace/shared/xfinaudio-v17-r3-evidence`: `native-fixes-red.log`, `native-fixes-build.log`, `native-fixes-green.log`. Source/test patch is105 changed lines across11 files, below400; manifest includes per-file hashes. SDD reviewed separately.

Focused command: `npm run build && node --test tests/renderer.workflow*.test.mjs tests/renderer.prep.test.mjs tests/preferences.test.mjs tests/renderer.preferences-app.test.mjs tests/renderer-controller.test.mjs tests/renderer.profiles-app.test.mjs`.

No full R3 Node/native result is claimed yet. The previous Python gate is unchanged/parent-owned; no additional aggregate was started. No engines, security, dependencies, versions, packaging, user data or provider/audio writes changed.

## Exact incremental native checklist

1. At outer1000×800 (native content1000×768), scroll0, Create default controls with a normal two-line status: verify Generate bounds fully above player top and legible. Repeat normal1440×940. Do not infer visual pass from compact CSS structural test.
2. Review→Ayuda IA→scroll down→primary Crear: verify task start visible and Generate fully accessible. Tool Back still restores its actual entry focus; sorting/background rerenders do not move scroll; drafts persist and AI consent still invalidates on route changes.
3. Request20 with8 eligible fixture tracks: warning says «Se seleccionaron8 de las20 pistas solicitadas» with actual spaces/values; unknown actionable warning unchanged. Without minutes quantity says requested; with minutes it says maximum and payload still uses real count cap.
4. Open Settings before scan, add synthetic folder, return Settings: label updates without Actualizar. Repeat with unsaved volume/watch edits and touched player volume; preserve draft, player volume, paused state and save/revision protections. Explicit Refresh remains functional.
5. In rendered Settings DOM, exactly one `settings-heading` and one dynamic `preferences-heading`; page and inner section references target their respective heading.

Mock app tests verify calls, state, exact quantities, revisions, focus/scroll invocation and no playback application. Parsed/source structural checks bound placement/ID contracts, not actual native pixel geometry, keyboard visibility or screen-reader behavior.
