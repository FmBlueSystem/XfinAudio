# Specification: UI Follow-up Polish

## Requirements

### R1. Sidebar icons
GIVEN the workflow sidebar THEN every item exposes a non-null icon, so narrow mode shows icons not blank rows.

### R2. Live Assistant margins
GIVEN the Live Assistant screen THEN its root layout uses contentsMargins 12 and spacing 8, matching other screens.

### R3. Next-step cue after scan
GIVEN a successful scan completes THEN the guidance text references the Build next step AND the Library proceed button is the primary action.

### R4. Persistent error banner
GIVEN an error occurs WHEN show_error_banner(text) is called THEN a persistent banner is visible with the text; clear_error_banner() hides it.

### R5. Build guidance grouping
GIVEN the Build screen THEN the contiguous guidance labels are children of a single panel container.

## Non-functional
- No UI test regressions; offscreen-Qt compatible; within 400-line budget.
