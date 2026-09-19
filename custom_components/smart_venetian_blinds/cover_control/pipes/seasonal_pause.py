"""SeasonalPausePipe — stop driving covers outside the configured season."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER
from custom_components.smart_venetian_blinds.cover_control.pipes.no_sun import is_no_sun
from homeassistant.components.cover import ATTR_CURRENT_POSITION, ATTR_CURRENT_TILT_POSITION
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_SET_COVER_POSITION
import homeassistant.util.dt as dt_util

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from datetime import date

    from custom_components.smart_venetian_blinds.cover_control.context import CoverContext
    from custom_components.smart_venetian_blinds.season import SeasonRestStore, SeasonWindow


class SeasonalPausePipe:
    """
    Suspend cover control outside the configured season.

    While the group is seasonally paused the cover is moved **once** to the
    configured rest position and then left alone until the season starts again.
    The drive is held back until the sun is above the horizon, so the pause never
    raises a cover at night, and it respects a manually closed cover the same way
    ``SleepProtectionPipe`` does — this pipe runs before it, so it has to apply
    that guard itself.

    The drive only happens on the first day the pause is observed. If it cannot
    run that day it is abandoned rather than left armed — a drive that fires weeks
    later, the moment a user happens to open the slats, is worse than no drive.

    Whether the drive has run is persisted per cover and per pause period (see
    ``SeasonRestStore``), so it survives a restart and re-arms when the season or
    the rest position is edited.

    While paused, ``in_no_sun`` is kept in step with the real sun position. The
    pipes behind this one never run during a pause, so without that the first
    cycle after the season resumes — just after midnight, in the dark — would look
    to ``NoSunPipe`` like a fresh no-sun period and fire its action.
    """

    POSITION_TOLERANCE_PERCENT = 2

    def __init__(self, season: SeasonWindow, store: SeasonRestStore, position_timeout_sec: int) -> None:
        """Initialize with the group's season window, its rest store and the position timeout."""
        self._season = season
        self._store = store
        self._position_timeout_sec = position_timeout_sec

    async def handle(self, ctx: CoverContext, call_next: Callable[[], Awaitable[bool]]) -> bool:
        """Handle pipe step."""
        today = dt_util.now().date()

        if not self._season.is_paused(today):
            return await call_next()

        # Keep the no-sun flag truthful so the season can resume at any hour.
        ctx.state.in_no_sun = is_no_sun(ctx)

        entity_id = ctx.config.entity_id
        if self._store.is_done(entity_id, self._season, today):
            LOGGER.debug("Cover %s: seasonally paused (%s), rest position already applied", entity_id, self._season)
            return False

        pending_since = self._store.pending_since(entity_id, self._season, today)
        if today > pending_since:
            # The drive missed its day. Firing it now — possibly months into the
            # pause, the moment a cover happens to become reachable — would be a
            # worse surprise than never parking the cover at all.
            LOGGER.info(
                "Cover %s: seasonal rest drive abandoned, pending since %s — leaving the cover where it is",
                entity_id,
                pending_since.isoformat(),
            )
            self._store.mark_done(entity_id, self._season, today)
            return False

        blocked = self._blocked_reason(ctx)
        if blocked is not None:
            LOGGER.debug("Cover %s: seasonally paused, rest drive deferred (%s)", entity_id, blocked)
            return False

        return await self._apply_rest_position(ctx, today)

    def _blocked_reason(self, ctx: CoverContext) -> str | None:
        """Return why the rest drive cannot run right now, or None if it can."""
        if ctx.calculation is None:
            return "sun below horizon"

        if not ctx.config.respect_manual_close:
            return None

        state = ctx.hass.states.get(ctx.config.entity_id)
        if state is None:
            return "cover unavailable"

        raw_tilt = state.attributes.get(ATTR_CURRENT_TILT_POSITION)
        if raw_tilt is None:
            return "tilt unavailable"

        try:
            tilt = float(raw_tilt)
        except (ValueError, TypeError):
            return "tilt unreadable"

        if tilt < ctx.config.manual_close_threshold:
            return "slats manually closed"
        return None

    async def _apply_rest_position(self, ctx: CoverContext, today: date) -> bool:
        """Drive the cover to the season rest position exactly once."""
        target = self._season.rest_position
        entity_id = ctx.config.entity_id

        state = ctx.hass.states.get(entity_id)
        if state is None:
            LOGGER.debug("Cover %s: state unavailable, retrying season rest drive next cycle", entity_id)
            return False

        current_position: int | None = None
        raw = state.attributes.get(ATTR_CURRENT_POSITION)
        with contextlib.suppress(ValueError, TypeError):
            current_position = int(raw) if raw is not None else None

        if current_position is not None and abs(current_position - target) <= self.POSITION_TOLERANCE_PERCENT:
            LOGGER.debug("Cover %s: seasonally paused, already at rest position %d%%", entity_id, target)
            self._store.mark_done(entity_id, self._season, today)
            return False

        LOGGER.info(
            "Cover %s: season %s over — driving to rest position %d%% and pausing until next season",
            entity_id,
            self._season,
            target,
        )
        await ctx.hass.services.async_call(
            "cover",
            SERVICE_SET_COVER_POSITION,
            {ATTR_ENTITY_ID: entity_id, "position": target},
            blocking=True,
        )
        await self._wait_for_position(ctx, target)
        self._store.mark_done(entity_id, self._season, today)
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
