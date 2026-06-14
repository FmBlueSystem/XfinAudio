# Specification: Auto-hide Missing Column in Library Screen

## Requirements

### R1. Default hidden state

**GIVEN** the Library screen is rendered  
**THEN** the "Missing" column is hidden by default.

### R2. Toggle visibility

**GIVEN** the Library screen is visible  
**WHEN** the user presses the "Show Missing" toggle  
**THEN** the "Missing" column becomes visible and the button text changes to "Hide Missing".

**GIVEN** the "Missing" column is visible  
**WHEN** the user presses the "Hide Missing" toggle  
**THEN** the "Missing" column is hidden and the button text changes to "Show Missing".

### R3. Row operations remain consistent

**GIVEN** the "Missing" column is hidden  
**WHEN** tracks are populated, filtered, sorted, or selected  
**THEN** the operation uses the correct column indices (Path remains the lookup key).

### R4. Accessibility

**GIVEN** the toggle button exists  
**THEN** it has an accessible name describing its action.

## Non-functional

- The change must not break existing Library screen tests.
- The change must stay within the 400-line review budget.
