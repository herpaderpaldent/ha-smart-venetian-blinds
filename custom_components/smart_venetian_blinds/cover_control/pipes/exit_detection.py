"""ExitDetectionPipe — detect manual open and set exit_paused."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER
from homeassistant.components.cover import ATTR_CURRENT_POSITION

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from custom_components.smart_venetian_blinds.cover_control.context import CoverContext


class ExitDetectionPipe:
    """
    Detect when the user has manually raised the cover above the exit threshold.

    When detected, set exit_paused=True and stop the pipeline for this cycle.
    On the next cycle, ExitPausedCheckPipe will prevent any further tracking.

    This check is skipped when ctx.first_sun_hit=True (the first tracking cycle
    after a no-sun period), which prevents false detection after no_sun_behavior="open"
    raised the cover to 100%.
    """

    async def handle(self, ctx: CoverContext, call_next: Callable[[], Awaitable[bool]]) -> bool:
        """Handle pipe step."""
        if not ctx.config.respect_manual_open:
            return await call_next()

        if ctx.first_sun_hit:
            # First tracking cycle after no-sun: bypass detection so the cover can
            # drive back down from whatever position no-sun behavior left it at.
            LOGGER.debug(
                "Cover %s: first sun hit after no-sun period, bypassing exit detection",
                ctx.config.entity_id,
            )
            return await call_next()

        state = ctx.hass.states.get(ctx.config.entity_id)
        if state is None:
            return await call_next()

        raw_position = state.attributes.get(ATTR_CURRENT_POSITION)
        if raw_position is None:
            return await call_next()

        try:
            current_position = int(raw_position)
        except (ValueError, TypeError):
            return await call_next()

        if current_position >= ctx.config.manual_open_threshold:
            LOGGER.debug(
                "Cover %s position at %d%% (>= threshold %d%%), setting exit-paused",
                ctx.config.entity_id,
                current_position,
                ctx.config.manual_open_threshold,
            )
            ctx.state.exit_paused = True
            return False

        return await call_next()
