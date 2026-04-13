"""TiltPipe — apply the calculated slat angle."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER
from custom_components.smart_venetian_blinds.sun.math import apply_tilt_inversion
from homeassistant.components.cover import ATTR_CURRENT_TILT_POSITION
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_SET_COVER_TILT_POSITION

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from custom_components.smart_venetian_blinds.cover_control.context import CoverContext
    from custom_components.smart_venetian_blinds.cover_control.controller import CoverConfig


class TiltPipe:
    """Apply the calculated slat tilt, respecting angle constraints and minimum change threshold."""

    async def handle(self, ctx: CoverContext, call_next: Callable[[], Awaitable[bool]]) -> bool:
        """Handle pipe step."""
        if ctx.calculation is None:
            return False

        tilt_percent = self._apply_angle_constraints(ctx.calculation.slat_tilt_percent, ctx.config)
        tilt_percent = apply_tilt_inversion(tilt_percent, ctx.config.invert_tilt)
        tilt_percent = max(tilt_percent, self._effective_min_tilt(ctx.config))

        state = ctx.hass.states.get(ctx.config.entity_id)
        if state is not None:
            raw_tilt = state.attributes.get(ATTR_CURRENT_TILT_POSITION)
            if raw_tilt is not None:
                try:
                    current_tilt = float(raw_tilt)
                    tilt_change = abs(tilt_percent - current_tilt)
                    if tilt_change < ctx.config.minimum_tilt_change:
                        LOGGER.debug(
                            "Cover %s tilt change %.1f%% is below threshold %d%%, skipping",
                            ctx.config.entity_id,
                            tilt_change,
                            ctx.config.minimum_tilt_change,
                        )
                        return False
                except (ValueError, TypeError):
                    pass

        LOGGER.debug(
            "Setting tilt for %s to %.1f%% (angle: %.1f°, inverted: %s)",
            ctx.config.entity_id,
            tilt_percent,
            ctx.calculation.slat_angle_deg,
            ctx.config.invert_tilt,
        )

        await ctx.hass.services.async_call(
            "cover",
            SERVICE_SET_COVER_TILT_POSITION,
            {ATTR_ENTITY_ID: ctx.config.entity_id, "tilt_position": int(round(tilt_percent))},
            blocking=True,
        )
        return True

    @staticmethod
    def _apply_angle_constraints(tilt_percent: float, config: CoverConfig) -> float:
        """Apply per-cover min/max angle bounds in standard (pre-inversion) tilt space."""
        if config.max_angle < 90:
            tilt_percent = max(tilt_percent, 100.0 * (1.0 - config.max_angle / 90.0))
        if config.min_angle > 0:
            tilt_percent = min(tilt_percent, 100.0 * (1.0 - config.min_angle / 90.0))
        return tilt_percent

    @staticmethod
    def _effective_min_tilt(config: CoverConfig) -> float:
        """Minimum tilt the integration may set."""
        base = float(config.manual_close_threshold) if config.respect_manual_close else 0.0
        angle_floor = 100.0 * (1.0 - config.max_angle / 90.0) if config.max_angle < 90 else 0.0
        return max(base, float(config.min_tilt_percent), angle_floor)
