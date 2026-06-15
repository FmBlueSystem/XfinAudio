# Phase 4: Visual Hierarchy

## Intent

Make the desktop UI communicate action priority at a glance: primary actions stand out,
secondary actions recede, sections are visually separated, and empty screens guide the user.

## Scope

- Primary actions (Scan, Recommend, Export) get larger buttons with accent colors.
- Secondary actions (Settings, Cancel, Back, Preview) get smaller, muted buttons.
- Add section dividers between controls and tables.
- Add empty-state illustrations for: no library, no tracks, no recommendation.

## Success criteria

1. Primary buttons carry `objectName="primaryAction"` and a larger minimum size.
2. Secondary buttons carry `objectName="secondaryAction"` and a smaller maximum size.
3. Section dividers (`QFrame.HLine`) separate controls from the table on each screen.
4. Empty-state labels exist for no library, no tracks, and no recommendation.
5. All tests pass and all verification commands pass.
