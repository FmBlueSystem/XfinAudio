# Observable requirements

## G1 Responsive generation
GIVEN valid preparation inputs WHEN generation begins THEN the UI continues processing events, all duplicate-generation routes are disabled, and busy progress is visible. GIVEN a successful current request WHEN it completes THEN its variants replace the prior plan once on the GUI thread.

## G2 Safe cancellation and recovery
GIVEN a previous valid plan WHEN a new request fails or is cancelled THEN the prior plan and applied recommendation remain available. GIVEN cancellation WHEN work reaches a cooperative checkpoint THEN remaining stages stop; any already-finishing stale result cannot replace the current state. GIVEN cancel then retry WHEN the old request later completes THEN only the newer request may publish. GIVEN window close during Prep WHEN its worker is still running THEN ownership is retained until it exits without forced termination.

## H1 Keyboard-visible explanations
GIVEN a transition table WHEN a row/cell is selected using the keyboard THEN plain-language transition context, warnings and relevant score explanations appear in a visible, selectable detail area without hovering. GIVEN data clear/replacement WHEN the prior selection is invalid THEN stale explanations clear. Compact controls and navigation remain reachable.

## I1 Destination truthfulness (decision pending)
Serato export labels and next steps must describe the actual crate destination and the separate report folder. A missing report folder must not imply that selecting it changes the crate's destination. Preserve existing writer behavior unless staging is explicitly selected for the scope before Apply.
