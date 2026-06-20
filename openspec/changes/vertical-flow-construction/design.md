# Design: Vertical flow construction foundation

## Architecture Direction

The vertical workflow should follow the documented dependency rule:

```text
Presentation -> Presentation adapters -> Application -> Domain
                                    Application -> Ports
Infrastructure -> Ports / Domain data models
```

## First Construction Path

```text
Library Scan -> Recommendation -> Playlist Save/Export
```

This path is selected because it exercises the real product backbone:

- `desktop` starts the action and renders progress/results.
- `desktop` controllers/coordinators translate UI events into commands.
- `application` coordinates scan/recommend/save/export use cases.
- `recommendation`, `library`, `quality`, and `exporting` own product rules.
- repositories/exporters/settings/audio adapters stay outside UI policy.

## Initial Slice Strategy

Start with a small application-level contract that describes the vertical workflow inputs and outputs without moving large UI code at once.

Recommended first implementation slice:

- Add focused tests for a vertical-flow application service or workflow facade.
- Reuse existing domain services and ports where possible.
- Keep desktop wiring changes minimal and explicit.
- Do not alter recommendation algorithms, export formats, or scan behavior.

## Safety

- No audio mutation.
- No DSP expansion.
- No live Serato DB V2 writes.
- No dependency changes unless separately approved with upper bounds and lockfile update.
- Preserve existing visible behavior.
