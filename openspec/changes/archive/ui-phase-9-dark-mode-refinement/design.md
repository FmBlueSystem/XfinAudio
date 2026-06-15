# Design: Dark Mode Refinement

## Decision question

How do we improve the dark theme without breaking existing styles?

## Alternatives considered

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Update theme.py colors/styles | Simple; centralized | May need multiple iterations | **Selected** |
| B. Add new theme file | Modular | More files to maintain | Rejected |
| C. Use Qt style sheets | Flexible | Harder to test | Rejected |

## Architecture impact

- `theme.py`: Update color constants and add hover/focus styles

## Affected files

- `src/xfinaudio/desktop/theme.py`
