"""PositionDrivePipe — drive cover to drive_position before tilting."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER
from custom_components.smart_venetian_blinds.cover_control.position import (
    async_wait_for_position,
    is_at_position,
    read_position,
)
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_SET_COVER_POSITION

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from custom_components.smart_venetian_blinds.cover_control.context import CoverContext


class PositionDrivePipe:
    """
    Drive the cover to drive_position before tilting.

    Always ensures the cover is at drive_position before TiltPipe applies
    the calculated angle. This is the core "drive-then-tilt" invariant.

    After the cover reports reaching the target position, an additional
    settling delay is observed before proceeding. This prevents premature
    tilt commands when a device reports the target position before its
    motor has physically finished travelling.
    """

    def __init__(self, position_timeout_sec: int, settling_delay_sec: int = 5) -> None:
        """Initialize with position timeout and optional post-drive settling delay."""
        self._position_timeout_sec = position_timeout_sec
        self._settling_delay_sec = settling_delay_sec

    async def handle(self, ctx: CoverContext, call_next: Callable[[], Awaitable[bool]]) -> bool:
        """Handle pipe step."""
        current_position = read_position(ctx.hass, ctx.config.entity_id)
        if current_position is None:
            LOGGER.warning("Cannot get position for %s, skipping", ctx.config.entity_id)
            return False

        if not is_at_position(current_position, ctx.config.drive_position):
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
            await async_wait_for_position(
                ctx.hass,
                ctx.config.entity_id,
                ctx.config.drive_position,
                self._position_timeout_sec,
            )
            if self._settling_delay_sec > 0:
                LOGGER.debug(
                    "Cover %s: settling delay %ds after position drive",
                    ctx.config.entity_id,
                    self._settling_delay_sec,
                )
                await asyncio.sleep(self._settling_delay_sec)

        return await call_next()
