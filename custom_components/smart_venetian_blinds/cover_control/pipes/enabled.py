"""EnabledPipe — skip disabled covers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from custom_components.smart_venetian_blinds.cover_control.context import CoverContext


class EnabledPipe:
    """Skip processing if the cover is disabled."""

    async def handle(self, ctx: CoverContext, call_next: Callable[[], Awaitable[bool]]) -> bool:
        """Handle pipe step."""
        if not ctx.config.enabled:
            LOGGER.debug("Cover %s is disabled, skipping", ctx.config.entity_id)
            return False
        return await call_next()
