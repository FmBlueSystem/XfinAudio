# Requirements

## R1 Visible application and explanations
GIVEN a fresh visible Build screen without a plan WHEN variants arrive THEN its table and Apply action become visible on the same render and a default variant is selected. GIVEN a selected variant WHEN selection changes THEN the track count, readiness and pool reasons are available inline without hovering. Existing selections survive unchanged renders.

## R2 Bundled assets
GIVEN source, installed-wheel or frozen runtime layouts WHEN a bundled asset is requested THEN the corresponding existing asset is resolved. GIVEN the real Spanish catalog WHEN Spanish is installed THEN Qt translates a known application string. The distributable wheel includes runtime catalogs and icons.

## R3 Accurate actionable metadata
GIVEN a fractional BPM WHEN shown in Library, Review or Metadata THEN the fractional value is retained without an unnecessary trailing .0. GIVEN a fresh Metadata screen WHEN a library is rendered THEN incomplete tracks are shown by default, missing fields use human labels, and the repair checklist is identifiable.

## R4 Prerequisites
GIVEN no complete selected anchor WHEN an anchor-dependent generation action is rendered THEN it is disabled and a visible next step leads to Library or metadata repair. Natural-language generation follows its actual prerequisite contract. Busy states cannot resurrect actions.

## R5 Compact layout
GIVEN a compact window WHEN Build is shown THEN controls do not crush the set-request input, and the application can use 1000x700 geometry. GIVEN the narrow Library table WHEN its columns adapt THEN Color remains readable according to the existing layout contract.
