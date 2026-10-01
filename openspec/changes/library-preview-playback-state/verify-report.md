# Focused verification

Four new failing regressions were observed before changing production code.
88 focused tests passed across lifecycle, Library preview/screen/path index and
player state-machine tests. Targeted Ruff lint/format and Pyright passed using
the project virtual environment for installed dependencies.

The first-Play preservation regression remains green. Sort may intentionally
replace table items, but no transient empty selection stops the surviving preview.
Removing the selected path publishes empty selection and stops it deliberately.

Broader Linux lifecycle and aggregate verification remain integration work.
This focused slice uses synthetic fixtures and does not establish native GUI acceptance.
