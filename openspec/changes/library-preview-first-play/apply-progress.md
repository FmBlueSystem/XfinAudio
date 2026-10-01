# Apply progress

Base: original-history 43edb7f6597788b4036718a7a498abd88a5f85f5.
RED reproduced first Play ending IDLE through MainWindow.show_tracks and a fake
QObject player. GREEN updates current cells by path without consulting cache
validity or initiating content render. The content cache remains invalid.
No media is decoded; the isolated SQLite fixture contains synthetic paths only.
