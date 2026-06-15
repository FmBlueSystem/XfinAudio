# Specification: Live Assistant Onboarding Guidance

## Requirements

### R1. Guidance banner

**GIVEN** the Live Assistant tab is shown with no current track  
**THEN** a guidance banner is visible explaining:
1. Pick a track to start the session (or use the candidate list).
2. Preview candidates with the play button; alerts flag risky transitions.
3. Press "Load Next" to commit the chosen track as the new current track.

### R2. Keyboard hints

**GIVEN** the Live Assistant tab is shown  
**THEN** a short hint mentions Space (play) and L (load next).

### R3. Empty-state fallback

**GIVEN** no candidates are available  
**THEN** the guidance banner remains visible and explains that scanning a library first populates candidates.

## Non-functional

- Stay within the 400-line review budget.
- No behavioral change to the load-next logic.
