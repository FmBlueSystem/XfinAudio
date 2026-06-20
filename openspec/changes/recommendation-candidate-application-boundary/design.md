# Recommendation Candidate Application Boundary Design

Add `xfinaudio.application.recommendation_candidates` as a thin application use-case boundary over the existing pure candidate-pool policy. Keep the recommendation algorithm unchanged in `xfinaudio.recommendation.candidate_pool` for this slice.

Update `MainWindow._desktop_recommendation_records()` to call the application boundary. Keep desktop DTO/type imports intact unless they are directly part of this boundary.
