# Responsive AI screen layouts

Keep the actual desktop usable at 1000×700 after expanding AI/local-assistant
controls. Give Create available height instead of an unconditional 280px cap;
keep Review actions and details reachable; keep Library filters and selected
track details from enlarging the window. Size Editor action cells and Live
history columns for their contents. No workflow, model, audio, provider,
persistence, dependency or navigation changes.

Risks: nested scrolling and altered table space. Verify shown MainWindow
geometry and actual captures with synthetic records, temporary HOME and no
network. Roll back individual layout commits. Success: requested compact
window remains 1000×700 and controls remain reachable at both target sizes.

Delivery: three chained review slices, each <=400 changed lines:
1. Library/Review compact layout, SDD and regression tests.
2. Adaptive Create viewport and confirmation/recovery regression tests.
3. Editor/Live table sizing, verification and screenshot evidence.
