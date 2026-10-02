# Observable corrections

- GIVEN a confirmed export receipt WHEN core disconnects after navigating away THEN a conditional last-export link opens the retained receipt without backend calls, changing source or invalidating previews. No link without a receipt.
- GIVEN a mounted editor draft WHEN core disconnects after navigating away THEN a conditional resume link opens the same draft without editor.open or writes. Existing disabled mutation rules remain. No link without a draft.
- GIVEN101 required or excluded tracks inside a closed disclosure WHEN Generate is attempted THEN the offending select/group opens and receives focus. Required wins when both lists are invalid; opening=closing still focuses closing.
- GIVEN cached Metadata WHEN returning from a pending Serato destination picker that is cancelled THEN filter/page/explanation DOM is preserved. Explicit Refresh and actual scan/library invalidation still fetch a fresh report.
