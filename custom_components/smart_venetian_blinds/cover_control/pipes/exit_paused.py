"""ExitPausedCheckPipe — skip all tracking when exit mode is active."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER
from homeassistant.components.cover import ATTR_CURRENT_POSITION

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from custom_components.smart_venetian_blinds.cover_control.context import CoverContext


class ExitPausedCheckPipe:
    """
    Skip all tracking when the cover is in exit-paused state.

    exit_paused is set by ExitDetectionPipe (auto-detection) or by the
    switch.<cover>_exit_mode entity (manual trigger).

    Auto-resume: if the cover position has dropped back below manual_open_threshold
    the user has lowered the cover again, so exit_paused is cleared and tracking
    resumes immediately.

    exit_paused is also cleared when the cover enters the no-sun period (NoSunPipe).
    """

    async def handle(self, ctx: CoverContext, call_next: Callable[[], Awaitable[bool]]) -> bool:
        """Handle pipe step."""
        if not ctx.state.exit_paused:
            return await call_next()

        if not ctx.config.respect_manual_open:
            ctx.state.exit_paused = False
            return await call_next()

        # Check whether the user has lowered the cover back below the threshold.
        state = ctx.hass.states.get(ctx.config.entity_id)
        if state is not None:
            raw = state.attributes.get(ATTR_CURRENT_POSITION)
            if raw is not None:
                try:
                    current_position = int(raw)
                    if current_position < ctx.config.manual_open_threshold:
                        LOGGER.debug(
                            "Cover %s position at %d%% (< threshold %d%%), clearing exit-paused",
                            ctx.config.entity_id,
                            current_position,
                            ctx.config.manual_open_threshold,
                        )
                        ctx.state.exit_paused = False
                        return await call_next()
                except (ValueError, TypeError):
                    pass

        LOGGER.debug(
            "Cover %s is in exit-paused state, skipping all tracking",
            ctx.config.entity_id,
        )
        return False
