# Verification
- RED: 3 About/packaging tests failed before implementation.
- GREEN: 32 focused About, PyInstaller and core translation checks passed.
- Spanish compiled-catalog check reproduced the host/MainWindow context mismatch
  and passed after the precise catalog repair.
- Focused type/lint/format checks pass.
- Full final exact-head gate and macOS CI belong to the integration coordinator;
  this slice does not claim a new native interactive or DMG validation.
