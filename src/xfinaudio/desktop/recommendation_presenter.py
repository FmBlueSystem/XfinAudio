"""Backward-compatible re-export of the pure recommendation pool selector.

The implementation moved to :mod:`xfinaudio.recommendation.pool` so it lives in the
recommendation domain and can be imported without pulling in the Qt-dependent desktop
package. This module is kept so existing importers continue to work.
"""

from __future__ import annotations

from xfinaudio.recommendation.pool import build_recommendation_pool

__all__ = ["build_recommendation_pool"]
