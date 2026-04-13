"""PositionDrivePipe — drive cover to drive_position before tilting."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER
from homeassistant.components.cover import ATTR_CURRENT_POSITION
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_SET_COVER_POSITION

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from custom_components.smart_venetian_blinds.cover_control.context import CoverContext


class PositionDrivePipe:
    """
    Drive the cover to drive_position before tilting.

    Always ensures the cover is at drive_position before TiltPipe applies
    the calculated angle. This is the core "drive-then-tilt" invariant.
    """

    POSITION_TOLERANCE_PERCENT = 2

    def __init__(self, position_timeout_sec: int) -> None:
        """Initialize with position timeout."""
        self._position_timeout_sec = position_timeout_sec

    async def handle(self, ctx: CoverContext, call_next: Callable[[], Awaitable[bool]]) -> bool:
        """Handle pipe step."""
        state = ctx.hass.states.get(ctx.config.entity_id)
        if state is None:
            LOGGER.warning("Cannot get state for %s, skipping", ctx.config.entity_id)
            return False

        raw_position = state.attributes.get(ATTR_CURRENT_POSITION)
        if raw_position is None:
            LOGGER.warning("Cannot get position for %s, skipping", ctx.config.entity_id)
            return False

        try:
            current_position = int(raw_position)
        except (ValueError, TypeError):
            LOGGER.warning("Invalid position value for %s, skipping", ctx.config.entity_id)
            return False

        if abs(current_position - ctx.config.drive_position) > self.POSITION_TOLERANCE_PERCENT:
            LOGGER.debug(
                "Driving %s from %d%% to %d%%",
                ctx.config.entity_id,
                current_position,
                ctx.config.drive_position,
            )
            await ctx.hass.services.async_call(
                "cover",
                SERVICE_SET_COVER_POSITION,
                {ATTR_ENTITY_ID: ctx.config.entity_id, "position": ctx.config.drive_position},
                blocking=True,
            )
            await self._wait_for_position(ctx, ctx.config.drive_position)

        return await call_next()

    async def _wait_for_position(self, ctx: CoverContext, target_position: int) -> bool:
        """Wait for cover to reach target position."""
        elapsed = 0.0
        interval = 0.5

        while elapsed < self._position_timeout_sec:
            state = ctx.hass.states.get(ctx.config.entity_id)
            if state is not None:
                raw = state.attributes.get(ATTR_CURRENT_POSITION)
                try:
                    current = int(raw) if raw is not None else None
                except (ValueError, TypeError):
                    current = None
                if current is not None and abs(current - target_position) <= self.POSITION_TOLERANCE_PERCENT:
                    LOGGER.debug("Cover %s reached position %d%%", ctx.config.entity_id, current)
                    return True
            await asyncio.sleep(interval)
            elapsed += interval

        LOGGER.warning(
            "Timeout waiting for %s to reach position %d%%",
            ctx.config.entity_id,
            target_position,
        )
        return False
