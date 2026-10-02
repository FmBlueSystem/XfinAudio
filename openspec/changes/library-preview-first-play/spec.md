# First-play contract

- GIVEN MainWindow.show_tracks populated a selected row and invalidated the render
  cache, WHEN Preview is clicked, THEN playback remains playing, selected paths and
  all QTableWidgetItem identities survive, including a subsequent state sync.
- GIVEN an already-rendered table, WHEN playing highlight changes, THEN only the
  affected existing cells and backgrounds change; content cache invalidation remains
  available for the normal content-render path.
