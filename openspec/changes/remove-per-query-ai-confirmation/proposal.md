# Remove per-query AI confirmation friction

## Why
Every AI request currently demands two per-query authorizations: an in-app consent
tick and a native macOS dialog ("¿Enviar solo esta solicitud?"). The maintainer
reports this as friction for every single consultation.

## What Changes
- Persist a new AI setting `autoAuthorize` (default OFF) in the profile settings.
- The native confirmation dialog gains "No volver a preguntar"; checking it and
  sending persists `autoAuthorize=true` through the normal AI settings flow.
- The Ajustes de IA panel gains the same toggle; saving works through
  `saveAiSettings` like `enabled`.
- With `autoAuthorize` ON, `ask()` skips `ai.confirmation` and the native dialog
  and sends `ai.run` directly; the renderer no longer requires the per-preview
  consent tick. Consent moves from per-request to an explicit, revocable
  settings decision. The disclosure text and payload review remain visible.
- Consent-first posture preserved: the setting is OFF by default, AI itself
  stays opt-in, and the toggle lives next to the AI enable switch.

## Impact
- Affected specs: optional-ai-assistance (consent/authorization requirement).
- Affected code: `src/xfinaudio/config/settings.py`, `src/xfinaudio/headless/ai_protocol.py`,
  `src/xfinaudio/headless/preferences.py`, `desktop-electron/src/security.ts`,
  `desktop-electron/src/optional-ai-host.ts`, `desktop-electron/src/main.ts`,
  `desktop-electron/renderer/optional-ai.ts`, `desktop-electron/renderer/optional-ai-view.ts`.
