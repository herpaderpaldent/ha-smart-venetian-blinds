"""ExitPausedCheckPipe — skip all tracking when exit mode is active."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from custom_components.smart_venetian_blinds.cover_control.context import CoverContext


class ExitPausedCheckPipe:
    """
    Skip all tracking when the cover is in exit-paused state.

    exit_paused is set by ExitDetectionPipe (auto-detection) or by the
    switch.<cover>_exit_mode entity (manual trigger). It is cleared automatically
    when the cover enters the no-sun period (NoSunPipe), so tracking resumes
    the next morning.
    """

    async def handle(self, ctx: CoverContext, call_next: Callable[[], Awaitable[bool]]) -> bool:
        """Handle pipe step."""
        if ctx.state.exit_paused:
            LOGGER.debug(
                "Cover %s is in exit-paused state, skipping all tracking",
                ctx.config.entity_id,
            )
            return False
        return await call_next()
