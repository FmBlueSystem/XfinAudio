# Design

Add a metadata selector to ExportSource, resolved against authorized records. Store exact records for the original plan_metadata_status_serato_export / plan_metadata_missing_field_serato_export. Preserve normal playlist readiness checks; metadata worklists have needs_review status and a specific repair-worklist warning. Reuse destination and native confirmation instead of a second write path. Renderer receives a callback for its exact filtered opaque IDs.
