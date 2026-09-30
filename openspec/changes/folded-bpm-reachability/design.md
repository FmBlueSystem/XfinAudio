# Design

Keep the production change inside playlist_service._bpm_reachable_from. Sort
eligible measurable candidates and the measurable anchor by BPM/path. Traverse
components using direct and half/double-time BPM windows. Validate candidate
edges with the unchanged shared comparator. A successor index skips visited
positions, avoiding repeated traversal of dense already-discovered regions and
avoiding an adjacency matrix. Conservatively pad window endpoints for rounding.
Preserve the old treatment of protected non-anchor controls and unknown BPM:
passthrough only, excluded as bridges. Preserve earliest sorted-component ties
and reconstruct output in input order. No model or persistence changes.

Tests independently enumerate all-pairs graph edges for small deterministic
random corpora, test boundaries and controls, reproduce the public failure, and
count comparator calls on a dense pool rather than assert wall-clock timing.
AGENTS.md's aggregate gate supersedes the older skill's redundant commands and
obsolete command-line coverage floor; pyproject.toml remains the floor owner.
