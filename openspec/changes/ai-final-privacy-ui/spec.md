# Requirements

## R1: Outbound path minimization
GIVEN a request with a relative POSIX or Windows audio path, including quoted
paths or filenames with spaces, WHEN interpreted through injected AI transport,
THEN the recognized path is replaced before transmission and musical intent
around it remains. Ordinary genre names and ratios remain intact.
GIVEN free text can contain unrecognizable private information, WHEN reviewing
AI settings, THEN disclosure precisely describes path redaction and cautions
against including private information; audio is never sent.

## R2: Deliberate saved-set deletion
GIVEN a selected saved set, WHEN Delete is clicked, THEN confirmation names the
complete set, states permanence, and defaults to Cancel. Cancellation or closing
preserves repository data; explicit acceptance deletes only that selected set.
GIVEN no selection, WHEN Delete is clicked, THEN no confirmation or delete occurs.

## R3: Spanish core controls
GIVEN Spanish is installed from the shipped catalog, WHEN opening reviewed AI
controls, THEN action, configuration, interpreted confirmation and deletion text
appear in Spanish with placeholders retained and their actual QObject contexts.
