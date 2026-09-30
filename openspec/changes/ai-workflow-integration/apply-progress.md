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

2026-09-30 expanded interpretation completion: the existing local query/edit/set
helpers are retained as fallbacks. Dedicated optional NaN structured-intent and
asynchronous UI slices now complete the original AI proposal on those screens;
Metadata/Live add optional evidence-only commentary. No provider is contacted by
development tests. Interim full suite: 3,084 pass, 94.12% coverage, four failures
limited to confirmed compact-layout and missing-button-tooltip regressions, being
repaired before final acceptance.

Responsive capture found long export destinations could force later screens
wider through the shared status line. RED reproduces the oversized window;
GREEN (12 shell checks) bounds and wraps plain status text while retaining the
complete destination in the tooltip and accessibility description.

All five optional remote assistants are installed in the actual main window,
with cancel on close and context invalidation during state rendering. Library
AI suggestions remain unapplied until the existing Apply action. Editor uses
existing musical preview/confirm/save boundaries. A new RED caught Live prose
surviving a set switch within the same library; GREEN invalidates after the
local session is refreshed so old commentary clears on that same sync.

With all optional assistant rows installed, one large-window Library visibility
check failed. Increasing the controls/table stretch ratio keeps all primary
controls visible at 1440x1000 while preserving the compact scroll and table
minimum. All 16 focused responsive/Library boundary checks pass.

Final review P1: saved exports inherited prior set removals/readiness. RED proved
both omitted A and wrongly inherited readiness. GREEN (41 transition/coordinator/
saved-service tests) exports exact [A,B] through the actual Serato writer in an
isolated temporary fixture; current missing metadata still blocks. Transition
recomputes scores, quality, readiness and explanation; clears only set-derived
removals/narration/Prep plan/variant, preserving global Library controls. Unknown
saved records are now explicitly incomplete rather than falsely marked complete.

Publication was subsequently authorized as a branch and draft PR only. Remote
main is still a812f26 at version 2.0.1. Candidate version is now 2.1.0 in both
pyproject and uv.lock; no dependency version changed. Offline fresh resolution was
unnecessary/unavailable in the cache, so the local-project lock version was
aligned and then uv lock --check --offline plus uv sync --locked --offline both
passed, building and installing the local 2.1.0 project without network access.
