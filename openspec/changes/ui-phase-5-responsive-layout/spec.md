# Specification: Responsive Layout

## Requirements

### R1. Width-driven sidebar sizing

**GIVEN** a window width at or above the narrow breakpoint
**THEN** `responsive_sidebar_width(width)` returns the wide sidebar width (180).

**GIVEN** a window width below the narrow breakpoint
**THEN** `responsive_sidebar_width(width)` returns the narrow sidebar width (120).

### R2. Narrow-window sidebar collapse

**GIVEN** the main window is resized below the narrow breakpoint
**THEN** the workflow sidebar collapses to icon-only navigation (labels hidden)
and its panel width becomes the narrow width.

**GIVEN** the main window is widened to or above the breakpoint
**THEN** the workflow sidebar restores full text labels and the wide width.

### R3. Full Screen mode

**GIVEN** the main window
**WHEN** `set_full_screen(True)` is called
**THEN** the sidebar panel and the status controls row are hidden.

**WHEN** `set_full_screen(False)` is called
**THEN** the sidebar panel and the status controls row are visible again.

### R4. Window geometry persistence

**GIVEN** a `WindowSettings` model with width, height, x, and y
**THEN** it round-trips through `AppSettings` JSON serialization unchanged.

**GIVEN** a window constructed with settings that carry a stored geometry
**THEN** the window restores that width and height on construction.
