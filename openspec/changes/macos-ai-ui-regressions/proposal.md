# macOS AI workflow UI regressions

Restore consistent saved-playlist activation and usable Review table height after
macOS CI exposed native Qt behavior absent from the Linux offscreen run.
Scope: saved-list keyboard/mouse activation, Review idle status layout, focused
regressions. No provider, audio, export or data-model changes. Risk: duplicate
activation or hidden status; explicit tests cover both. Rollback is this bounded
commit. Success: unchanged shell flow and table-space assertions pass, with
platform-independent activation and no empty status-row overhead. Under 400 lines.
