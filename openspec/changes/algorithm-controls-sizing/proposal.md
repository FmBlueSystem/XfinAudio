# Preserve requested controls and slot coverage
User-authorized detailed algorithm audit found end/locked tracks removed by prefix trimming, Prep sequencing without requested count, and rounded arc sizing returning 8 minutes for a 9-minute slot with ample 4-minute records.
Scope: control-aware final selection, forwarding Prep count, duration coverage/reported shortage. No DSP, audio writes, UI changes, publish or deployment.
Success: mandatory controls survive compatible feasible trim or explicit failure; terminal remains terminal; available duration covers booked slot; shortages are explicit. Preserve strategy ordering and manual-prefix precedence.
Rollback: revert this isolated slice. Risk: trimming may create new BPM seams; validate all new seams and report failure rather than fabricate legality.
Delivery: chained algorithm slices (reachability separately owned); 400-line review budget per implementation slice, verification evidence additional.
