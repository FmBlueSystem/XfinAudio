# Requirements

- Given the desktop library bootstrap is running, when `listLibrary()` rejects, then the library page shows a
  recovery panel with a non-empty reason and a "Reintentar cargar biblioteca" control.
- Given that failure, when the normal idle drain runs (`getLibraryStatus`, preferences) and settles, then the
  recovery panel is still visible with its reason; idle work for unrelated features is otherwise unchanged.
- Given the recovery panel is shown, when the user activates retry, then the renderer calls `listLibrary()` again
  and never calls the folder chooser or a rescan, and never writes profile data.
- Given a retry is already in progress or any operation is in the gate, when the user activates retry again, then
  no second load is started.
- Given a retry (or the original bootstrap) succeeds, when the library is applied, then the recovery panel is
  hidden, the library is rendered, and the operation status is hidden as before.
- The recovery panel is present in the shipped renderer markup and is hidden until a bootstrap failure occurs.

## Bounded first paint (ODD work unit 2)

- Given a library with more rows than one window, when the Library first renders, then the table shows at most 200 rows,
  `library-visible-count` still reports the full match count, and a distinct note states how many of how many are shown.
- Given more matches than the shown window, when the user activates "Mostrar 200 pistas más", then the table reveals up to
  200 more matches and the affordance disappears once every match is shown.
- Given a search, metadata filter, AI display filter, sort or refreshed library, when the visible identity changes, then
  the window resets to its first 200 rows while search, filter and sort still operate on the whole library.
- Given a large library, when the app boots on the Library page, then the Prep selects are not fully populated yet; when
  Prep is opened (or already active while the library refreshes), then every track is offered in the selects and existing
  selections survive, including dirty "No disponible" choices.
- The Library keeps its Tonalidad/key column and per-row metadata for every rendered row.
