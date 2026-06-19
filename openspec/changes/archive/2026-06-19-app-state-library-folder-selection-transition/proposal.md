# Proposal: App State Library Folder Selection Transition

## Intent
Move the business/state policy for selecting a library folder and resetting scan-dependent state out of `LibraryController` into a pure AppState transition.

## Scope
- Add a pure transition that sets `selected_folder` and clears scan-dependent recommendation/library state immutably.
- Keep settings persistence, labels, guidance copy, widget updates, and idle-action refresh in the desktop controller.
- Cover the transition with a RED-first unit test.

## Out of Scope
- Changing scan execution, metadata parsing, Serato export, or audio files.
- Refactoring table population or persisted-library restoration in this slice.

## Success Criteria
- `LibraryController.set_selected_folder()` delegates AppState replacement to a pure transition.
- The original AppState remains unchanged by the transition helper.
- Focused and full verification gates pass.
