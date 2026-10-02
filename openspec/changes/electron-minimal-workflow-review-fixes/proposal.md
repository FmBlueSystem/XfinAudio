# Bounded minimal-workflow corrections

Fix four independent-review P2 regressions in V17-r2 only: offline receipt/draft reachability, required/excluded limit error focus, and interrupted metadata-return cache loss. V17/V17-final stay immutable. Preserve three-step hierarchy with two conditional read-only resume links, no new primary navigation. No controller/backend/main/preload/security/provider/audio changes. Roll back via the frozen V17-final baseline. One correction review piece, target<400 total changed lines; split explicitly if exceeded.
