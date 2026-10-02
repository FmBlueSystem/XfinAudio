# Requirements
- GIVEN malformed TLV, unsafe track paths, or bytes inconsistent with the plan, WHEN confirmed, THEN reject before creating directories, backups or targets.
- GIVEN a final target symlink, WHEN writing or rolling back, THEN refuse without changing its referent.
- GIVEN an occupied backup name (including a symlink), WHEN overwriting a crate, THEN exclusively create a different backup and preserve every prior backup/referent.
- GIVEN a successful write, THEN publish the complete bytes through a same-directory atomic replacement and return the actual backup location.
- GIVEN failed post-write readback, THEN restore the prior bytes or remove a newly created target and raise a typed actionable error; never return a success result.
- GIVEN concurrent target replacement, THEN do not silently overwrite or delete an unrelated replacement during recovery.
