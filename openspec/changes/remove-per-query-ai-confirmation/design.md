# Design: persisted automatic authorization

## Decisions
- **Where the state lives**: the core's frozen `AiSettings` pydantic model gains
  `auto_authorize: bool = False`; the headless preferences layer maps it to the
  camelCase protocol field. The Node side stays stateless: `ask()` reads the
  setting through a new `autoAuthorize()` dependency backed by the inline
  read-only `ai.status` core method, so no second source of truth exists.
- **How the dialog persists it**: `dialog.showMessageBox` supports a checkbox;
  main persists `autoAuthorize=true` best-effort after a confirmed send with the
  box ticked (stale-revision errors are swallowed: Ajustes remains the reliable
  path). `enabled` is sent as `true` because a confirmed send implies it.
- **Why the host skip is safe**: ownership of the preview id is still enforced
  (`previews` set from `prepare`), the recipient was validated at prepare time,
  and the core still owns disclosure, payload retention and result validation.
  Only the human dialog is skipped, exactly what the setting means.
- **Renderer gating**: `canAsk` accepts either the per-preview consent tick or
  the persisted automatic authorization; the ask notice names which authority
  is being used, so the UI never lies about a dialog that will not appear.
- **Fail-closed response validation**: `statusCopy` requires `autoAuthorize` as
  a boolean so a stale core cannot silently disable the user's choice.
