"""Compatibility wrapper for recommendation candidate-pool policy.

New code should import from ``xfinaudio.recommendation.candidate_pool``.
"""

from __future__ import annotations

from xfinaudio.recommendation.candidate_pool import anchor_preflight_warnings, build_recommendation_pool

__all__ = ["anchor_preflight_warnings", "build_recommendation_pool"]
