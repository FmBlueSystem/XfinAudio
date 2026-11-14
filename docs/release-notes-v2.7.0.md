## Serato export

The export screen no longer starts by asking for a folder. When it opens with a
selection to export it looks for `_Serato_` on its own: first under each scanned
library folder, then at the root of the music drive (a library in
`/Volumes/dd/_Lossless/por_genero` uses `/Volumes/dd/_Serato_`), and finally in
`~/Music` when that folder is on the same volume. A destination found this way is
shown as detected automatically and the screen goes straight to the preview
step; **Cambiar carpeta _Serato_** keeps the manual picker as a secondary action.
When nothing is found, the screen says so in Spanish, explains that opening
Serato once with the drive connected creates the folder, and offers the manual
choice instead of opening a dialog on its own. A folder chosen by hand may now be
the drive root or `~/Music`: the `_Serato_` folder it directly contains is used,
and anything else keeps the existing `invalid_destination` refusal. Detection and
registration keep the same-volume rule, canonical folder and backup checks as
before, and nothing is written until the final confirmation.
