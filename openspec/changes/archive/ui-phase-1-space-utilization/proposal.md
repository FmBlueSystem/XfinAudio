# Phase 1: Space Utilization

## Intent

Make the track table use available vertical space instead of being constrained to 190px height.

## Scope

- Remove `setMaximumHeight(190)` constraint on `tracks_table`
- Increase `setMinimumHeight` to 400px
- Set `QSizePolicy.Expanding` for vertical growth
- Remove unused height constants from theme.py

## Success criteria

1. Track table expands to fill available vertical space
2. Users can see 15-20 tracks instead of 6
3. All tests pass
4. All verification commands pass
