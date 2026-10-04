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
