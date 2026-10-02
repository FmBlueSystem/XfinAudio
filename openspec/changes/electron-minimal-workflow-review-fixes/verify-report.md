# Verification

Fresh V17-r2 build+81 affected tests passed,0 failed/cancelled/skipped/todo. Strict RED first:44-test baseline run failed7 intended cases. Evidence under `/workspace/shared/xfinaudio-v17-r2-evidence`: `corrections-red.log`, `corrections-build.log`, `corrections-green.log`, exact patch and manifest.

Command: `npm run build && node --test tests/renderer.editor-app.test.mjs tests/renderer.prep.test.mjs tests/renderer-controller.test.mjs tests/renderer.workflow-structure.test.mjs tests/renderer.workflow.test.mjs tests/renderer.restored-app.test.mjs tests/serato-export.test.mjs tests/renderer.editor.test.mjs` from desktop-electron.

Source/test correction piece: 65 changed lines across8 files, below400. SDD is separately reviewed. No Python/controller/main/preload/security/dependency/audio/provider changes. Historical408 passing tests belong to V17-final; no full V17-r2 claim yet. Parent checkpoint precedes full Node; unchanged Python aggregate is already parent-owned.

## Incremental native checklist only

1. On the existing synthetic export fixture, confirm the retained receipt is reachable via Última exportación after Library navigation and core disconnection. Verify filename/destination/count/backup receipt, focus/scroll to receipt and disabled export/reveal actions. Opening/repeating the link must make zero backend calls and preserve existing source/name/preview state. Link absent before a receipt.
2. Open a synthetic saved editor, make an unsaved name/order change, navigate to Library and disconnect core. Ver borrador must reopen the same mounted draft/dirty state with disabled mutations and no editor.open call; verify focus/scroll to the draft. Link absent without a mounted draft.
3. With101 synthetic known tracks and count100, select101 required, close its disclosure, Generate: open the disclosure and focus required. Repeat101 excluded; with both, required takes priority. Confirm no generation request, and opening=closing still focuses closing.
4. In Metadata retain a real filter/query/page/explanation, open Serato, begin destination chooser, return via Back while pending, then cancel chooser. All metadata DOM/state stays intact with no second report request. Explicit Refresh and a real library invalidation must still reload appropriately.

The fixture tests establish state/calls and actual-HTML placement; they do not establish native keyboard/layout/visibility. Full native matrix is unnecessary for this bounded correction; parent owns this incremental checklist.
