# Apply progress

2026-09-30: Baseline ab56f27 is clean. Four isolated worktrees assigned. No
production code changed during initialization. Metadata and shell integration
are coordinator-owned. All development tests use synthetic metadata, credential
placeholders and injected transports; no live provider request is authorized.

Metadata slice: RED collection failed because the repair-guidance module did not
exist. GREEN now passes 25 metadata domain/widget/layout checks. Guidance uses
actual missing values, prioritizes locked tracks then fewer fields, and never
writes. Selected-track explanation and empty-library reset verified. Ruff and
focused Pyright with the project interpreter pass.

Editor shell slice: RED proved missing editor route and widget; a second RED
proved stale loaded-id after editor clear. GREEN: 75 navigation/state/playlist
checks pass. Editor appended at index 7, enabled only for an idle loaded set;
sidebar/stack/state synchronization preserves existing indices and snapshots.

Live/narrator shell slice: RED proved unavailable ready-session navigation and
in-flight narrator surviving a recommendation switch. GREEN: 42 domain/navigation
and actual shell interaction tests pass, including current-set reranking and
exclusion invalidation. Cancellation is wired, configuration route follows in the
Settings integration slice. Empty-library guidance now hides its empty panel.

Editor integration: actual QListWidget Return-key opening, button-click preview,
Apply, Save and Back verified against a temporary SQLite repository. Preview and
Apply leave the saved set untouched; only Save persists. Settings route verified
with the actual modal event loop and Cancel, leaving AI disabled. Shared component
lifecycle and shell integration currently pass all focused checks.

Create integration: actual modal Configure AI routes from Build and Review now
pass; local candidate-route snapshots are supplied before worker execution.
Independent acceptance identified unsaved draft loss at app-close. RED reproduced
both Close choices without a prompt; GREEN verifies default Cancel keeps the
window alive, Discard closes, and neither implicitly saves the draft.

Keyboard acceptance found Return was globally opening Library playback instead
of saved sets once the window event loop settled. Stronger RED processes show
 events before pressing Return. GREEN (11 shell checks) scopes Return to the
Library table and Delete to the Review table, preserving text fields and native
saved-list activation. Existing shortcut names/key sequences remain unchanged.
