# Design
Use importlib.metadata at the About boundary, escape the value in rich text, and
translate a stable Version {version} template. Catch only PackageNotFoundError.
PyInstaller copy_metadata includes the installed project's metadata alongside
assets. pyproject.toml remains the source of truth for the version.
