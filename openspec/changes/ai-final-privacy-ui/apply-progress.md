# Apply progress

2026-09-30: proposal/spec/design/tasks complete; bounded three-slice plan approved
by coordinator. Starting R1 RED before production changes. All fixtures and keys
are synthetic; use temporary HOME, offscreen Qt, and the existing shared venv.

R1 RED: eight missing-redaction assertions and one disclosure assertion failed
before production changes. GREEN: recognize relative audio suffixes with POSIX
or Windows separators, including filename spaces and fully quoted paths with
spaced directory names. REFACTOR: preserve genre/ratio prose before and after
paths by requiring whitespace-free unquoted directory components. Free-text
privacy disclosure now accurately describes known/recognizable path removal.

R2 RED: three prompt/persistence cases failed against immediate deletion. GREEN:
the existing signal now requires explicit named, permanent-deletion confirmation;
Cancel is default. Raw names are stored separately, so parentheses and markup
cannot truncate the selected name; the dialog renders plain text. REFACTOR/VERIFY:
actual modal Enter activation cancels; no coordinator/repository behavior changed.
