# Design: UI Follow-up Polish

- R1: add QStyle standard icons per sidebar item; narrow collapse keeps icon, blanks only text.
- R2: set layout.setContentsMargins(12,12,12,12) and setSpacing(8) in LiveAssistantScreen.__init__.
- R3: in the scan-complete guidance path, set guidance to a Build-pointing message; set Library proceed button objectName=primaryAction.
- R4: add an errorBanner QLabel (hidden, styled) in the central layout; show_error_banner/clear_error_banner methods; wire _fail_recommendation as the representative adopter; clear on successful recommendation.
- R5: wrap recommendation_vs_copilot/constraint_explanation/recommendation_summary labels in a QFrame buildGuidancePanel.

## Safety
Pure UI; no audio/DSP/Serato writes.
