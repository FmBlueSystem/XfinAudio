# Feature: AI Copilot Fase 1 — NL intent -> DJSetIntent -> prep variants

## Goal

Bring the proven demo flow into the app: a service-layer copilot that turns a
DJ's natural-language request into a validated, vocabulary-normalized
DJSetIntent, plus the app parameter that points at the credential file, plus a
minimal desktop chat panel wired to build_prep_copilot_plan.

## Context

- Base branch feat/ai-copilot-fase1 = main@42b9cdc + merge of feat/ai-nan-adapter
  (11b5df4). Adapter already validated live (deepseek-v4-flash + glm5.3-flash OK).
- Demo findings that MUST be addressed here:
  1. LLM vocabulary normalization: engine compares genre case-sensitively; the
     copilot must map LLM strings onto library vocabulary (genres) and validate
     strategy against available_strategies().
  2. glm5.3-flash explanations need timeout > 30s (not part of this slice; UI
     must allow a longer timeout).
- Key lives at /Users/freddymolina/Desktop/XfinAudio/apiIA.env (bare key,
  chmod 600). Settings store the PATH, never the key value.
- Shared main worktree is busy with the 1.9.0rc1 release (peer session); all
  work happens in ../fase1-copilot.

## Tasks

1. [x] Branch feat/ai-copilot-fase1 from main@42b9cdc + merge adapter.
2. [x] T1 service layer:
       - `AiSettings` (enabled: bool = False, env_file: Path | None = None) in
         config/settings.py, added to AppSettings following the repo's
         versioned-settings conventions; persistence round-trip tests.
       - `src/xfinaudio/ai/intent_copilot.py`: extract_intent(user_request,
         tracks, *, model, timeout, transport) -> DJSetIntent — LLM chat ->
         JSON -> pydantic validation; title->path mapping from the provided
         library (case-insensitive); genre normalization; strategy validated
         against available_strategies() with harmonic_journey fallback;
         flag-off -> clear NanConfigError. Fully offline tests (fake transport).
       - additive exports in ai/__init__.py.
3. [x] Verify T1: 101 targeted + 2144 full suite passed; ruff clean; pyright 0 errors (independently re-verified by orchestrator).
4. [x] Work-unit commits: 00f87c0 (uv.lock sync chore) + bc2b524 (feat(ai) T1).
5. [ ] T2 desktop UI: minimal chat panel in the prep flow surface
       (explore desktop/ screens first; delegate writer with narrow surfaces;
       follow render-contract rules — the 4-screen signature caches require
       invalidation if tables are written directly).
6. [ ] Verify T2 + work-unit commit T2.
7. [ ] Merge feat/ai-copilot-fase1 into main AFTER the peer's release window
       closes; push remains a user decision.

## Constraints

- The LLM never selects tracks or orders them; it only fills the intent struct.
- The key value never appears in errors, logs, settings, or tests.
- No new third-party dependencies (stdlib urllib only).
- Do not block the peer release: no writes to the shared repo worktree.

## Evidence

- T1 commit: bc2b524 feat(ai): natural-language intent copilot service
- uv.lock note: the 1.8.3->1.9.0rc1 lock sync was kept (pyproject on this branch is
  1.9.0rc1 from the peer release commit 42b9cdc; the lock was stale at branch point).
- T2 integration note from writer: extract_intent has no env_file param yet;
  the desktop slice (T2) must wire AiSettings.env_file (startup env var or
  explicit call) so the stored path actually reaches the adapter.
