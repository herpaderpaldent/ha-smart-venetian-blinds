"""
Pipeline context for cover control.

Contains the per-cover persistent tracking state and the per-cycle execution context
passed through the cover control pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from custom_components.smart_venetian_blinds.cover_control.controller import CoverConfig
    from custom_components.smart_venetian_blinds.sun.math import SlatCalculationResult
    from homeassistant.core import HomeAssistant


@dataclass
class CoverTrackingState:
    """
    Persistent per-cover tracking state across coordinator update cycles.

    Replaces the group-level flags sun_has_hit_facade, is_first_facade_hit,
    no_sun_action_applied, and obstacle_was_blocking with two cover-specific booleans.
    """

    exit_paused: bool = False
    """
    True when the user (or auto-detection) has triggered exit mode for this cover.
    Set by ExitDetectionPipe when position >= manual_open_threshold, or by the
    exit_mode switch entity. Cleared automatically when the sun leaves the facade
    (entering the no-sun period) so tracking resumes the next morning.
    """

    in_no_sun: bool = False
    """
    True while this cover is in a no-sun period and the no-sun action has already
    been applied. Prevents re-applying the action on every coordinator update cycle.
    Cleared when the sun returns to the facade.
    """


@dataclass
class CoverContext:
    """
    Per-cycle execution context passed through the cover control pipeline.

    Each call to Pipeline.run() creates a fresh CoverContext. The ``state`` field
    holds the persistent CoverTrackingState which the pipes may mutate; callers
    are responsible for persisting those mutations between cycles.
    """

    config: CoverConfig
    calculation: SlatCalculationResult | None
    hass: HomeAssistant
    state: CoverTrackingState

    first_sun_hit: bool = field(default=False, init=False)
    """
    Set to True by NoSunPipe when transitioning from in_no_sun=True back to sun-active.
    Signals ExitDetectionPipe to skip the position check for this one cycle so the
    cover can drive back down after a no_sun_behavior="open" raised it to 100%.
    Not persisted — only valid for the current pipeline run.
    """
