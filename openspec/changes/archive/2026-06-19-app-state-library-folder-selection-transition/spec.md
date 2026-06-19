# Spec: App State Library Folder Selection Transition

## Requirement: Library folder selection is a pure AppState transition

The system MUST set the selected library folder and reset scan-dependent recommendation/library state through a pure AppState transition.

### Scenario: Selecting a folder replaces state immutably

- GIVEN AppState has a previous selected folder, scanned records, lookup map, and recommendation-derived data
- WHEN a new folder is selected
- THEN the transition MUST return a new AppState instance
- AND the selected folder MUST be the new folder
- AND scan-dependent records and recommendation outputs MUST be cleared
- AND the original AppState MUST remain unchanged.

### Scenario: Desktop controller keeps UI and persistence responsibility

- GIVEN a user chooses a folder in the desktop UI
- WHEN the controller applies the selection
- THEN settings persistence and widget guidance remain controller responsibilities
- AND state replacement policy is delegated to the pure transition helper.
