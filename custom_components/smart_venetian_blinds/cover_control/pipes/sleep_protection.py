"""SleepProtectionPipe — skip cycle if user manually closed slats."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER
from homeassistant.components.cover import ATTR_CURRENT_TILT_POSITION

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from custom_components.smart_venetian_blinds.cover_control.context import CoverContext


class SleepProtectionPipe:
    """
    Skip the current cycle if sleep protection is active.

    Sleep protection is a per-cycle tilt check only — it does not write any
    persistent state. If the tilt is below the manual_close_threshold, we assume
    the user manually closed the slats and skip everything for this cycle.

    This pipe runs before NoSunPipe and PositionDrivePipe so that neither
    no-sun behavior (e.g. raising the cover) nor the position drive can disturb
    a sleeping user.

    Fail-safe: when ``respect_manual_close`` is enabled and the cover state or
    tilt value is temporarily unavailable (entity not yet loaded, device not
    reporting tilt), the pipe blocks rather than passing through.  This prevents
    NoSunPipe from raising the cover to 100% during an HA restart race condition
    or while the motor is moving and tilt is transiently None.
    """

    async def handle(self, ctx: CoverContext, call_next: Callable[[], Awaitable[bool]]) -> bool:
        """Handle pipe step."""
        if not ctx.config.respect_manual_close:
            return await call_next()

        state = ctx.hass.states.get(ctx.config.entity_id)
        if state is None:
            LOGGER.debug(
                "Cover %s: state unavailable, sleep protection blocking as fail-safe",
                ctx.config.entity_id,
            )
            return False

        raw_tilt = state.attributes.get(ATTR_CURRENT_TILT_POSITION)
        if raw_tilt is None:
            LOGGER.debug(
                "Cover %s: tilt position unavailable, sleep protection blocking as fail-safe",
                ctx.config.entity_id,
            )
            return False

        try:
            current_tilt = float(raw_tilt)
        except (ValueError, TypeError):
            LOGGER.debug(
                "Cover %s: invalid tilt value %r, sleep protection blocking as fail-safe",
                ctx.config.entity_id,
                raw_tilt,
            )
            return False

        if current_tilt < ctx.config.manual_close_threshold:
            LOGGER.debug(
                "Cover %s tilt at %.1f%% (below threshold %d%%), sleep protection active — skipping cycle",
                ctx.config.entity_id,
                current_tilt,
                ctx.config.manual_close_threshold,
            )
            return False

        return await call_next()
