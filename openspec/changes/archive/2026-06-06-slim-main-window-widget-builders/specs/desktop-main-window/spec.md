# Delta for Desktop Main Window

## ADDED Requirements

### Requirement: Private Widget Builder Extraction

The system MUST extract the `MainWindow` constructor's widget creation and intrinsic widget configuration into a private `_build_widgets()` builder while preserving the existing public desktop window contract.

#### Scenario: Public widget attributes remain available after widget-builder extraction

- GIVEN a `MainWindow` instance is constructed in an offscreen Qt environment after widget-builder extraction
- WHEN callers access the public widget attributes that existed before the extraction
- THEN each attribute MUST still exist on `MainWindow`
- AND each attribute MUST refer to a usable Qt widget with the same externally observable role as before the extraction.

#### Scenario: Initial widget intrinsic configuration remains unchanged

- GIVEN a `MainWindow` instance is constructed after widget-builder extraction
- WHEN the window title, public widget attributes, labels, table headers, table selection behavior and mode, initial enabled and visible states, label word-wrap, and label size constraints are inspected
- THEN each inspected value MUST match the behavior before the extraction.

#### Scenario: Widget builder remains a private implementation detail

- GIVEN existing callers import or construct `MainWindow`
- WHEN widget creation is moved into `_build_widgets()`
- THEN callers MUST NOT be required to import, instantiate, or depend on any new public widget-builder or panel-builder API.

### Requirement: Constructor Orchestration Safety

The system MUST preserve a safe `MainWindow` construction order so every extracted step observes the state and widgets it depends on.

#### Scenario: Constructor steps run in dependency-safe order

- GIVEN `MainWindow` construction runs after widget-builder extraction
- WHEN the constructor orchestrates setup
- THEN it MUST initialize constructor state before building widgets
- AND it MUST build widgets before connecting widget signals
- AND it MUST connect widget signals before applying visual design
- AND it MUST apply visual design before applying the compact layout
- AND it MUST apply the compact layout before installing the central widget.

#### Scenario: Signal and visual-design setup observe built widgets

- GIVEN `_connect_widget_signals()` and visual design setup run during construction
- WHEN those steps access widget attributes
- THEN every widget attribute they depend on MUST already exist
- AND signal-driven behavior MUST remain externally observable as before the extraction.

### Requirement: PR2 Boundary Preservation

The system MUST keep this PR2 slice limited to widget creation and intrinsic widget configuration extraction, without layout/page extraction or product behavior changes.

#### Scenario: Layout and page assembly remain in the constructor slice

- GIVEN the widget-builder extraction is implemented for PR2
- WHEN the change is reviewed
- THEN central widget assembly, page layout assembly, workflow tab layout assembly, and page-builder extraction MUST NOT be introduced in this slice.

#### Scenario: Product and UX behavior remain unchanged

- GIVEN a user performs existing scan, filter, recommendation, review, export, or metadata workflows after PR2
- WHEN those workflows are observed
- THEN user-visible labels, copy, layout, visual styling, workflow order, table contents, enabled states, visibility states, and outcomes MUST match the behavior before the extraction.

### Requirement: Offscreen Widget Builder Characterization Coverage

The system MUST validate the widget-builder extraction with automated Qt characterization coverage that runs offscreen and does not depend on real display rendering.

#### Scenario: Widget builder contract is covered offscreen

- GIVEN the test suite runs in an offscreen Qt environment
- WHEN `MainWindow` construction is exercised after widget-builder extraction
- THEN tests MUST verify preserved public widget attributes, initial widget intrinsic configuration, labels, table headers, visibility states, enabled states, and tab contract without requiring a real display.

#### Scenario: Table selection configuration is covered offscreen

- GIVEN the test suite runs in an offscreen Qt environment
- WHEN `tracks_table` and `prep_copilot_table` are inspected after construction
- THEN tests MUST verify their selection behavior and selection mode match the behavior before widget-builder extraction.
