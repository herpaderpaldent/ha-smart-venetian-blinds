"""SeasonalPausePipe — stop driving covers outside the configured season."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER
from homeassistant.components.cover import ATTR_CURRENT_POSITION
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_SET_COVER_POSITION
import homeassistant.util.dt as dt_util

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from custom_components.smart_venetian_blinds.cover_control.context import CoverContext
    from custom_components.smart_venetian_blinds.season import SeasonWindow


class SeasonalPausePipe:
    """
    Suspend cover control outside the configured season.

    While the group is seasonally paused the cover is moved **once** to the
    configured rest position and then left alone until the season starts again.
    The one-time rest drive is deferred until the sun is above the horizon
    (``ctx.calculation is not None``) so the pause never raises a cover in the
    middle of the night.

    Sensors keep updating during the pause — only cover movement stops. When the
    season starts again, the cover's tracking state is reset so the first cycle
    re-evaluates drive-then-tilt from scratch.
    """

    POSITION_TOLERANCE_PERCENT = 2

    def __init__(self, season: SeasonWindow, position_timeout_sec: int) -> None:
        """Initialize with the group's season window and the position timeout."""
        self._season = season
        self._position_timeout_sec = position_timeout_sec

    async def handle(self, ctx: CoverContext, call_next: Callable[[], Awaitable[bool]]) -> bool:
        """Handle pipe step."""
        if not self._season.is_paused(dt_util.now().date()):
            if ctx.state.season_rest_applied:
                LOGGER.debug(
                    "Cover %s: season %s started again — resuming sun tracking",
                    ctx.config.entity_id,
                    self._season.describe(),
                )
                ctx.state.season_rest_applied = False
                ctx.state.exit_paused = False
                ctx.state.in_no_sun = False
            return await call_next()

        if ctx.state.season_rest_applied:
            LOGGER.debug(
                "Cover %s: seasonally paused (season %s), rest position already applied",
                ctx.config.entity_id,
                self._season.describe(),
            )
            return False

        if ctx.calculation is None:
            LOGGER.debug(
                "Cover %s: seasonally paused, deferring rest drive until the sun is up",
                ctx.config.entity_id,
            )
            return False

        return await self._apply_rest_position(ctx)

    async def _apply_rest_position(self, ctx: CoverContext) -> bool:
        """Drive the cover to the season rest position exactly once."""
        target = self._season.rest_position

        state = ctx.hass.states.get(ctx.config.entity_id)
        if state is None:
            LOGGER.debug(
                "Cover %s: state unavailable, retrying season rest drive next cycle",
                ctx.config.entity_id,
            )
            return False

        current_position: int | None = None
        raw = state.attributes.get(ATTR_CURRENT_POSITION)
        with contextlib.suppress(ValueError, TypeError):
            current_position = int(raw) if raw is not None else None

        if current_position is not None and abs(current_position - target) <= self.POSITION_TOLERANCE_PERCENT:
            LOGGER.debug(
                "Cover %s: seasonally paused, already at rest position %d%%",
                ctx.config.entity_id,
                target,
            )
            ctx.state.season_rest_applied = True
            return False

        LOGGER.info(
            "Cover %s: season %s over — driving to rest position %d%% and pausing until next season",
            ctx.config.entity_id,
            self._season.describe(),
            target,
        )
        await ctx.hass.services.async_call(
            "cover",
            SERVICE_SET_COVER_POSITION,
            {ATTR_ENTITY_ID: ctx.config.entity_id, "position": target},
            blocking=True,
        )
        await self._wait_for_position(ctx, target)
        ctx.state.season_rest_applied = True
        return True

    async def _wait_for_position(self, ctx: CoverContext, target_position: int) -> bool:
        """Wait for the cover to reach the target position."""
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
                    return True
            await asyncio.sleep(interval)
            elapsed += interval

        LOGGER.warning(
            "Timeout waiting for %s to reach season rest position %d%%",
            ctx.config.entity_id,
            target_position,
        )
        return False
