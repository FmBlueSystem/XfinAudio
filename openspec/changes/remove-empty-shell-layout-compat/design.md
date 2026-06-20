# Design: Remove empty shell layout compatibility surface

Delete the empty layout compatibility module and remove its import/install call from `MainWindow`. Keep `shell_state_compat` and the `shell_compat` state facade unchanged.
