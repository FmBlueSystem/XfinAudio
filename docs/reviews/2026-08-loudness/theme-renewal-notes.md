# Theme Renewal — "Spectrum" Palette

Celebration refresh for the EBU R128 loudness-analysis milestone. This is a
visual refresh of the existing dark theme, not a redesign: the layout, the
component structure and the Serato warm accent are untouched.

There is only one theme variant in the app (`_DJ_VISUAL_STYLESHEET` in
`src/xfinaudio/desktop/theme.py`). No light variant exists, so none was added.

## Design intent

The app's identity is a deep blue-black console with a cold cyan accent. The
renewal keeps both anchors and adds the missing half of the spectrum:

- Surfaces go **deeper and cooler**, so bright accents read as emitted light
  rather than painted-on color.
- The cyan accent becomes a brighter **signal cyan**, and the primary action
  gradient now sweeps **aqua → cyan** instead of staying on one hue — a
  two-hue sweep that reads like a spectrum bar.
- Selection moves from a flat marine blue to **violet**, the high end of the
  spectrum. Selection is the most-repeated color in the UI (tables, sidebar,
  library rows), so this is where the refresh is actually felt.
- The warm amber (`#ffb000`) stays exactly as-is: it is the Serato export and
  status-warning identity color, and it is the warm end of the same spectrum.

## Before / after

### Surfaces

| Role | Before | After |
| --- | --- | --- |
| Window background | `#0b0f14` | `#080c12` |
| Panel surface | `#111923` | `#0f1721` |
| Elevated surface | `#17212c` | `#151f2b` |
| Table background | `#101820` | `#0e161e` |
| Table alternate row | `#14202a` | `#121d27` |
| Header section | `#151e28` | `#131c26` |
| Table corner button | `#182635` | `#16222f` |
| Tooltip background | `#1a2633` | `#182430` |
| Disabled surface | `#141a21` | `#12181f` |

Rationale: every surface drops ~2–3% luminance and picks up a touch more blue.
Deeper black makes the new accents look emissive; the relative step between
base / panel / elevated is preserved so depth cues are unchanged.

### Text

| Role | Before | After |
| --- | --- | --- |
| Primary text | `#edf5ff` | `#eaf4ff` |
| Secondary text (`QLabel`) | `#d7e4f2` | `#cfe0f0` |
| Muted / guidance text | `#9fb3c8` | `#93aac4` |
| Table header text | `#5caeb8` | `#63d3d8` |
| Disabled text | `#66717d` | `#6b7683` |

Rationale: the text ramp is pulled slightly cooler and its steps widened, so
primary / secondary / muted separate more clearly on the darker base. Header
text moves from a dull teal to a brighter aqua that belongs to the new accent
family — this pair gained the most contrast (6.57 → 9.69).

### Accent and highlight

| Role | Before | After |
| --- | --- | --- |
| Signal accent (focus, hover border, tooltip border) | `#00d4ff` | `#2ce8f5` |
| Primary action gradient | `#39e4ff` → `#00b8df` | `#3ef0d2` → `#00c2e6` |
| Primary action hover | `#63ecff` → `#00c8f2` | `#6ff7de` → `#22d6f7` |
| Text on accent | `#061018` | `#04121a` |
| Selection | `#005b86` | `#463ac4` |
| Active selection / selected row | `#0078b4` | `#5a4be0` |
| Serato export gradient | `#ffd36a` → `#ffb000` | unchanged |
| Status amber | `#ffb000` | unchanged |

Rationale:

- **Signal cyan `#2ce8f5`** — same hue family as `#00d4ff`, pushed up in
  lightness and slightly desaturated so it survives on the darker background
  without blooming. Identity stays instantly recognizable.
- **Aqua → cyan sweep** — the old primary button was a single-hue gradient, so
  it read as a flat blue slab. Crossing from `#3ef0d2` to `#00c2e6` gives the
  main call to action a directional energy, like a level meter filling.
- **Violet selection `#463ac4` / `#5a4be0`** — the old marine blue collided
  with the accent cyan (same hue family), so a selected row and a focused
  control were hard to tell apart. Violet is unambiguous, sits opposite the
  warm amber, and completes the spectrum reading. The active variant gained a
  full contrast point over the old `#0078b4` (4.83 → 5.97).

### Borders

| Role | Before | After |
| --- | --- | --- |
| Subtle border | `#2d3744` | `#2a3646` |
| Strong border | `#344456` | `#32425a` |
| Panel border | `#263544` | `#243444` |
| Divider / grid line | `#1e2d3a` | `#1c2b3b` |
| Header separator | `#2a3847` | `#283746` |
| Input hover border | `#445971` | `#46617f` |
| Disabled border | `#202832` | `#1e2732` |

Rationale: borders track the surfaces down in luminance and up in blue so the
edge-definition ratio against the new backgrounds stays constant.

## Contrast ratios (WCAG AA, dark theme)

Computed with the WCAG 2.x relative-luminance formula. AA body text needs
4.5:1; every pair below clears it, and the accent/selection pairs improved.

| Pair | After | Ratio | Before |
| --- | --- | ---: | ---: |
| Body text on window | `#eaf4ff` on `#080c12` | 17.62 | 17.49 |
| Label text on window | `#cfe0f0` on `#080c12` | 14.53 | 14.89 |
| Guidance text on window | `#93aac4` on `#080c12` | 8.20 | 8.93 |
| Status amber on panel | `#ffb000` on `#0f1721` | 9.84 | 9.66 |
| Table text on table background | `#eaf4ff` on `#0e161e` | 16.39 | 16.28 |
| Table text on alternate row | `#eaf4ff` on `#121d27` | 15.34 | 15.05 |
| Header text on header background | `#63d3d8` on `#131c26` | 9.69 | 6.57 |
| Selected row text | `#ffffff` on `#463ac4` | 7.89 | 7.39 |
| Active selected row text | `#ffffff` on `#5a4be0` | 5.97 | 4.83 |
| Sidebar selected item text | `#eaf4ff` on `#463ac4` | 7.09 | 6.73 |
| Primary button text | `#04121a` on `#3ef0d2` | 13.19 | 12.52 |
| Secondary button text | `#cfe0f0` on `#151f2b` | 12.33 | 12.61 |
| Serato button text | `#121212` on `#ffd36a` | 13.18 | 13.18 |
| Default button text | `#eaf4ff` on `#24354a` | 11.22 | 12.03 |
| Input text on input background | `#eaf4ff` on `#0f1721` | 16.21 | 16.09 |
| Tooltip text | `#eaf4ff` on `#182430` | 14.16 | 13.96 |
| Filter chip text on accent | `#04121a` on `#2ce8f5` | 12.62 | 10.83 |

The three pairs that dipped slightly (label, guidance, default button) each
lost under 0.9 of a point and stay far above AA — the cost of widening the
text ramp for better hierarchy. Disabled controls are WCAG-exempt and are
skipped by the contrast test, as before.

## Files touched

Theme definition and the files that replicate a theme constant:

- `src/xfinaudio/desktop/theme.py` — the stylesheet.
- `src/xfinaudio/desktop/screens/library_screen.py`,
  `src/xfinaudio/desktop/library_screen_rendering.py` — `_ROW_COLOR_EVEN`,
  `_ROW_COLOR_ODD`, `_ROW_COLOR_SELECTED` (duplicated in both files).
- `src/xfinaudio/desktop/library_screen_builder.py` — checked filter chip.
- `src/xfinaudio/desktop/menu.py`,
  `src/xfinaudio/desktop/screens/review_screen.py`,
  `src/xfinaudio/desktop/screens/live_assistant_screen.py` — inline muted-text
  color, aligned to the single `#93aac4` token.

Tests:

- `tests/test_theme_dark_mode.py` — background constant and focus-outline pin
  updated; two new tests pin the sixteen key palette colors and re-check the
  selection highlights against white text.
- `tests/test_library_screen_preview.py`, `tests/test_main_window.py` — pinned
  color literals updated to the new values.

## Deliberate non-changes

- **Semantic status colors** (`#1fd16a` ready, `#ffb000` needs-review,
  `#ff4d4f` blocked, and their `#1a3a2a` / `#3a3010` / `#4a1a1a` backings) were
  left alone. They are traffic-light semantics rather than brand palette,
  they are duplicated across five UI files plus six test assertions, and
  changing them buys no visual renewal for a large blast radius.
- **`#ff4444`** in `live_assistant_screen.py` belongs to that same status
  family and was left with it.
- **No color-token module was introduced.** The row colors are duplicated
  between `library_screen.py` and `library_screen_rendering.py` — pre-existing
  debt, out of scope for a palette refresh, and worth a separate cleanup.

## Verification

- `uv run pytest -q` → 1678 passed.
- `uv run ruff check .` → clean. `uv run ruff format --check .` → 288 files
  already formatted.
- `uv run pyright` → 0 errors, 0 warnings.

Note: `tests/test_main_window.py::test_main_window_scan_enables_cancel_and_updates_progress_then_disables_on_success`
failed once under `pytest-randomly` ordering with a `QThread: Destroyed while
thread is still running` warning. It passes on a clean checkout and with this
change under fixed ordering — a pre-existing order-dependent flake in the scan
worker teardown, unrelated to the palette. Not fixed here (out of scope).
