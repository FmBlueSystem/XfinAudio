# Specification: Quick Filter Bar

## Requirements

### R1. Filter bar visibility

**GIVEN** the Library screen is shown
**THEN** a filter bar is visible above the track table

### R2. Filter buttons

**GIVEN** the filter bar is shown
**WHEN** the user clicks a filter button
**THEN** the button is highlighted and the table is filtered

### R3. Clear filters

**GIVEN** one or more filters are active
**WHEN** the user clicks "Clear Filters"
**THEN** all filters are reset and the table shows all tracks

### R4. Active filter count

**GIVEN** one or more filters are active
**THEN** a badge shows the count of active filters
