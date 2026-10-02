# Qt-free loudness workflow

Restore the existing FFmpeg EBU R128/completion/tag-writing workflow, original three loudness settings and configured Prep loudness policy. Keep the existing single enabled setting: it gates analysis and automatic tag/comment writing, with no separate tag-write switch. In the new runtime, a read-only exact-track preview and explicit native confirmation precede a write-capable run; merely importing legacy enabled defaults never begins audio mutation.

Only copied/synthetic fixtures may be exercised by automation. Production UI makes scope and comment replacement clear. Preserve original measurements, cache identity refresh, cancellation/commit drainage and bounded concurrency. Add descriptor-bound writes and app-owned original-byte backups so a swapped path cannot redirect an authorized write. No live Serato or provider calls. Optional AI and standalone packaging remain subsequent slices.

Chained review plan, each publication unit <=400 changed lines: confined backup/write boundary; settings/policy parity; preview/session/backend composition; cancellation and shutdown; trusted main/IPC confirmation; library loudness/status/settings UI; source/native fixture verification. Split units further before any publication. Original Qt workflow remains available.
