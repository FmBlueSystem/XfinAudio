# Design

Keep existing controller boundaries and immutable state. Guard Create layout
observation and deferred reveal against incomplete/deleted widgets; defer revealing
until the resizable scroll content has reached its current minimum height. Distinguish
completed-result invalidation from active cancellation in OptionalAssistController.
Use a resizable scroll area for Live session content, compact vertical sizing for
optional AI, and explicit candidate action minimums. Preserve read-only commentary,
local ranking, worker retention, stale-result checks and all existing signals.
