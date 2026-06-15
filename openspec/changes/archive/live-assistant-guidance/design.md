# Design: Live Assistant Onboarding Guidance

## Decision question

How do we teach the DJ the Live Assistant flow without bloating the screen?

## Alternatives considered (Arbor-style)

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Permanent guidance banner at the top | Always visible. | Takes vertical space. | **Selected.** |
| B. Collapsible "How it works" expander | Clean when collapsed. | Hidden by default; user may never open it. | Rejected. |
| C. First-run tooltip overlay | Discoverable once. | Annoying on every reopen. | Rejected. |

## Architecture impact

`LiveAssistantScreen._build_ui` adds a `QLabel` with a 3-step guidance string at the top of the layout. Hidden when a current track is loaded to save space (replaced by the now-playing widget).

## Affected files

- `src/xfinaudio/desktop/screens/live_assistant_screen.py`
- `tests/test_screens.py` (or wherever the live assistant screen is tested)

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato Database V2 writes.
