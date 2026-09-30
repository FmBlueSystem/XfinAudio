# Verification — 2026-09-30

## Requirements

- R1: real shown MainWindow stays exactly 1000×700 and 1440×1000 with selected
  track loudness details and expanded query editor. Three table rows remain
  visible; controls are scroll-reachable; full controls fit on the larger view.
- R2: all three local Review details can be reached inside the scroll body at
  both sizes. Bottom navigation remains inside the window. Existing keyboard
  details and table-space regressions pass.
- R3: real disabled-AI recovery and synthetic interpreted requests reveal the
  relevant buttons at both sizes. Create's large viewport exceeds 500px;
  repeated state sync does not reset manual scrolling. No provider calls.
- R4: each styled Remove button fits horizontally and vertically inside the
  table viewport and its cell; measured style padding is included in sizing.
- R5: Live Title/Artist columns share all spare width; numeric/time columns use
  content widths. Current track names wrap at compact widths.

## Checks

191 focused tests pass across responsive geometry, Build, Review, keyboard
Review details, Library, local queries, Editor, Live, tooltip coverage, and the
MainWindow compact loaded-Build regression. Ruff check, Ruff format --check,
and Pyright (explicit shared virtualenv interpreter) pass for all touched code.
Actual QWidget.grab images inspected at 1000×700 and 1440×1000 with synthetic
records and fresh temporary HOME; no audio files, real keys or network calls.
Captures are delivered separately to the integrating parent.

No full release gate, dependency change, push, merge, deployment, audio writes
or real Serato export was performed. Parent must rerun final integration tests
and captures after adding the separately developed optional AI helper rows.

## Separate finding

A long global Export Preview status path can widen all later screens. This
belongs to the MainWindow status owner and was reported separately; it is not
caused by the screen layouts and is not changed in this scope.
