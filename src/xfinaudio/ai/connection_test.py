"""The synthetic text sent by an explicitly requested connection test.

This module is the single definition of that literal: the live headless probe in
``xfinaudio.headless.ai_execution`` sends it, and the Electron security layer
whitelists it for the ``connection`` surface. The Qt dialog state machine that
also lived here was removed with the Qt desktop in ``4e31a3a``; the Electron
panel and the headless backend own that interaction now.
"""

from __future__ import annotations

PROBE_MESSAGE = "Reply with OK. XfinAudio connection test."
