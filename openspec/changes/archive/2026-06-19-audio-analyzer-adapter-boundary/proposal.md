# Proposal: Audio analyzer adapter boundary

## Intent

Introduce an explicit spectral analyzer contract so scan/workers can depend on an analyzer boundary instead of hard-wiring the concrete analyzer call.

## Scope

In scope: analyzer port, default concrete adapter, dependency injection seams in scan service and spectral completion worker, tests with fake analyzers.

Out of scope: new DSP, audio mutation, classification changes, storage changes, UI changes, live Serato DB V2 writes.
