# Requirements

- GIVEN a current saved playlist WHEN Return or keypad Enter is pressed THEN its
  editor opens once and the key cannot activate unrelated parent controls.
- GIVEN the saved list WHEN arrows or mouse double-click are used THEN navigation
  remains native and a double-click opens once. Empty lists do not open anything.
- GIVEN the search input WHEN Return is pressed THEN search runs, not playlist open.
- GIVEN Review without narrator status WHEN laid out THEN empty status uses no
  vertical space; all three tables retain the existing four-row/65% contract.
- GIVEN narrator progress, error or completion WHEN its text changes THEN the
  message is visible; clearing it returns its space to the tables.
