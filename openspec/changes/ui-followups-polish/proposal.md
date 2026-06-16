# Proposal: UI Follow-up Polish (distribution + flow)

## Intent

Resolve the five UI follow-ups deferred from the distribution/export-gate change, each a small,
evidence-backed fix from the UI audit.

## Scope (in)

1. **Sidebar icons** — give each workflow item a real icon so narrow-window mode shows icons
   instead of blank rows (`main_window.py` sidebar + responsive collapse).
2. **Live Assistant margins** — root layout sets no margins/spacing; align to the 12/8 used by
   every other screen (`live_assistant_screen.py`).
3. **Next-step cue after scan** — after a successful scan, guidance explicitly points to Build and
   the Library proceed button is the primary action.
4. **Persistent error banner** — a dismissible error banner that stays visible instead of relying
   only on the transient status label (`main_window.py`).
5. **Build guidance grouping** — wrap the contiguous guidance labels in a bordered panel to reduce
   vertical noise (`build_screen.py`).

## Out of scope

- Full QSS migration of LiveAssistant inline styles; rewiring every error path through the banner
  (the main recommendation-failure path is wired as the representative adopter).

## Success criteria

1. Each sidebar item has a non-null icon.
2. LiveAssistant root layout margins are 12 and spacing 8.
3. After scan completion the guidance text references the Build next step.
4. `show_error_banner(text)` makes a persistent banner visible; `clear_error_banner()` hides it.
5. The grouped Build guidance labels share a panel container.
6. All verification commands pass; no UI test regressions.

## Review budget

~150 prod + ~120 test lines; single PR within budget.
