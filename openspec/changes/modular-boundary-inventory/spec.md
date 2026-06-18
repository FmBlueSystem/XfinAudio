# Modular Boundary Inventory Specification

## Requirement 1: Functional inventory

GIVEN a maintainer needs to understand XfinAudio responsibilities
WHEN they open the architecture inventory
THEN they can see each major functionality grouped into an independent module with current files, target owner, UI boundary, dependencies, and test coverage.

## Requirement 2: Business policy outside desktop

GIVEN recommendation candidate selection is business policy
WHEN desktop code needs a recommendation candidate pool
THEN it imports the policy from a non-UI recommendation module rather than owning the algorithm in `xfinaudio.desktop`.

## Requirement 3: Strategy value boundary

GIVEN UI strategy controls display friendly labels but domain code expects internal strategy names
WHEN Prep Copilot receives a strategy value
THEN a pure domain resolver accepts either the internal name or the built-in display label and returns the internal strategy name.

## Requirement 4: Unit-testable core modules

GIVEN a module contains pure recommendation or strategy-selection logic
WHEN behavior changes
THEN focused unit tests cover that behavior without instantiating `MainWindow` or requiring Qt widgets.
