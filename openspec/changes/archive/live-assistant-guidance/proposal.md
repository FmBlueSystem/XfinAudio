# Proposal: Live Assistant Onboarding Guidance

## Intent

The Live Assistant is fully implemented but users do not know how to use it. Add visible guidance explaining the three-step flow (set current track -> preview candidates -> load next) and a sample run-through.

## Scope

- Add a guidance banner at the top of `LiveAssistantScreen` with a 3-step explanation.
- Add a "How it works" expand/collapse section.
- Add keyboard shortcut hints (already in code: Space to play, L to load next).
- Tests: assert the guidance labels are visible on first render.

## Success criteria

1. Guidance banner is visible when the screen is empty.
2. Guidance text explains: set current track, preview, load next.
3. All existing tests pass.
4. All verification commands pass.
