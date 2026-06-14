# Delta for desktop-main-window

## MODIFIED Requirements

### Requirement: Search Filter Update Timing

The search filter in `MainWindow` MUST debounce keystroke input by 150 ms before applying the filter, so that only one filter call fires per typing burst.
(Previously: filter was applied synchronously on every keystroke event with no debounce delay.)

#### Scenario: Filter fires once after a typing burst

- GIVEN a library with 10 000+ tracks is loaded
- WHEN the user types several characters in quick succession within 150 ms
- THEN the filter MUST fire exactly once after the burst ends, not once per keystroke

#### Scenario: Filter result is identical to synchronous version

- GIVEN any valid search query string
- WHEN the debounced filter eventually fires
- THEN the set of visible tracks MUST be identical to what the non-debounced filter would have produced for the same query

#### Scenario: Immediate filter on programmatic clear

- GIVEN the search field is cleared programmatically or via paste
- WHEN the clear or paste action completes
- THEN an immediate filter call (≤ one timer cycle) is acceptable without violating the debounce contract

### Requirement: Tab Render Isolation

`_sync_state` MUST only call `.render()` on the screen belonging to the currently visible tab; hidden tab screens MUST NOT be rendered during a state sync.
(Previously: `_sync_state` called `.render()` on all screens regardless of tab visibility.)

#### Scenario: Only visible tab screen renders on sync

- GIVEN the application is on tab N with tab M hidden
- WHEN `_sync_state` is called
- THEN `.render()` MUST be called for the screen of tab N
- AND `.render()` MUST NOT be called for the screen of tab M

#### Scenario: Tab switch triggers render for newly visible screen

- GIVEN tab M was hidden during the last `_sync_state` call
- WHEN the user switches to tab M
- THEN the screen for tab M MUST call `.render()` with the latest state before being displayed

#### Scenario: All existing UI tests pass

- GIVEN the existing UI test suite
- WHEN run after the lazy-render change
- THEN all tests MUST pass without modification
