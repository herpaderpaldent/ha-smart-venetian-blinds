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
    """

    async def handle(self, ctx: CoverContext, call_next: Callable[[], Awaitable[bool]]) -> bool:
        """Handle pipe step."""
        if not ctx.config.respect_manual_close:
            return await call_next()

        state = ctx.hass.states.get(ctx.config.entity_id)
        if state is None:
            return await call_next()

        raw_tilt = state.attributes.get(ATTR_CURRENT_TILT_POSITION)
        if raw_tilt is None:
            return await call_next()

        try:
            current_tilt = float(raw_tilt)
        except (ValueError, TypeError):
            return await call_next()

        if current_tilt < ctx.config.manual_close_threshold:
            LOGGER.debug(
                "Cover %s tilt at %.1f%% (below threshold %d%%), sleep protection active — skipping cycle",
                ctx.config.entity_id,
                current_tilt,
                ctx.config.manual_close_threshold,
            )
            return False

        return await call_next()
