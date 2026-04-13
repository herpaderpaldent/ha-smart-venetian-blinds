"""
NoSunPipe — handle no-sun period and manage no-sun state transitions.

Responsibilities:
- Detect when there is no sun on the facade (calculation is None, sun behind facade,
  or sun elevation below the cover's obstacle threshold).
- On the first no-sun cycle: reset exit_paused, mark in_no_sun, apply the no-sun action.
- On subsequent no-sun cycles: skip (action already applied).
- When sun returns: clear in_no_sun, set ctx.first_sun_hit so ExitDetectionPipe skips
  its check this one cycle (prevents false exit detection after no_sun_behavior="open"
  raised the cover to 100%).
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from custom_components.smart_venetian_blinds.cover_control.context import CoverContext
    from custom_components.smart_venetian_blinds.cover_control.controller import CoverConfig

from homeassistant.components.cover import ATTR_CURRENT_POSITION
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_SET_COVER_POSITION, SERVICE_SET_COVER_TILT_POSITION


class NoSunPipe:
    """
    Manage no-sun detection, state transitions, and no-sun action dispatch.

    The no-sun action is applied exactly once per no-sun period:
    - Reflection protection (if enabled and sun was on facade today) sets a minimum tilt.
    - Otherwise the configured no_sun_behavior is dispatched.

    Reflection protection and no_sun_behavior are mutually exclusive: reflection protection
    is effectively a conditional set_to_percent for blocking reflected/diffuse glare,
    active when the sun was tracking the facade earlier today.
    """

    POSITION_TOLERANCE_PERCENT = 2

    def __init__(self, position_timeout_sec: int) -> None:
        """Initialize with position timeout for the no-sun open action."""
        self._position_timeout_sec = position_timeout_sec

    async def handle(self, ctx: CoverContext, call_next: Callable[[], Awaitable[bool]]) -> bool:
        """Handle pipe step."""
        no_sun = self._is_no_sun(ctx)

        if no_sun:
            return await self._handle_no_sun(ctx)

        # Sun is active — check if we're transitioning back from a no-sun period
        if ctx.state.in_no_sun:
            LOGGER.debug(
                "Cover %s: sun returned after no-sun period, clearing in_no_sun, bypassing exit detection",
                ctx.config.entity_id,
            )
            ctx.state.in_no_sun = False
            ctx.first_sun_hit = True  # signals ExitDetectionPipe to skip this cycle

        return await call_next()

    @staticmethod
    def _is_no_sun(ctx: CoverContext) -> bool:
        """Return True if the sun is not hitting the facade for this cover."""
        if ctx.calculation is None or ctx.calculation.sun_is_behind_facade:
            return True
        if (
            ctx.config.obstacle_elevation_deg > 0
            and ctx.calculation.sun_elevation_deg <= ctx.config.obstacle_elevation_deg
        ):
            return True
        return False

    async def _handle_no_sun(self, ctx: CoverContext) -> bool:
        """Apply no-sun action (once) and update state."""
        if ctx.state.in_no_sun:
            LOGGER.debug("Cover %s: already in no-sun period, skipping repeat action", ctx.config.entity_id)
            return False

        # First no-sun cycle: reset exit_paused (clean start for tomorrow) and apply action.
        ctx.state.exit_paused = False
        ctx.state.in_no_sun = True

        if self._is_reflection_protection_active(ctx):
            return await self._apply_reflection_protection(ctx)

        return await self._dispatch_no_sun_behavior(ctx)

    @staticmethod
    def _is_reflection_protection_active(ctx: CoverContext) -> bool:
        """Return True if reflection protection should override the no-sun behavior."""
        if not ctx.config.reflection_protection_enabled:
            return False
        # Reflection protection requires the sun to have been on the facade today
        # (tracked by in_no_sun transitioning from False with previous sun activity).
        # We check by whether we came from a tracking cycle, which is implicit:
        # if in_no_sun was previously False and we had sun activity, sun_has_hit_facade
        # would have been set. We preserve this via the context: if the calculation
        # indicates the sun IS behind the facade (not below horizon), it was tracking today.
        if ctx.calculation is None:
            return False  # sun is below horizon — no facade hit this cycle
        # Sun is behind facade or below obstacle: if it's behind the facade specifically,
        # that means it was tracking earlier today.
        return ctx.calculation.sun_is_behind_facade

    async def _apply_reflection_protection(self, ctx: CoverContext) -> bool:
        """Apply reflection protection minimum tilt."""
        min_tilt = self._effective_min_tilt(ctx.config)
        tilt = max(float(ctx.config.reflection_protection_min_tilt), min_tilt)
        LOGGER.debug(
            "Cover %s: reflection protection active, setting tilt to %.1f%%",
            ctx.config.entity_id,
            tilt,
        )
        await ctx.hass.services.async_call(
            "cover",
            SERVICE_SET_COVER_TILT_POSITION,
            {ATTR_ENTITY_ID: ctx.config.entity_id, "tilt_position": int(round(tilt))},
            blocking=True,
        )
        return True

    async def _dispatch_no_sun_behavior(self, ctx: CoverContext) -> bool:
        """Dispatch the configured no_sun_behavior."""
        behavior = ctx.config.no_sun_behavior
        if behavior == "keep_last":
            LOGGER.debug("Cover %s: no sun — keeping last position", ctx.config.entity_id)
            return False
        if behavior == "open":
            return await self._no_sun_open(ctx)
        if behavior == "close":
            return await self._no_sun_close(ctx)
        if behavior == "set_to_percent":
            return await self._no_sun_set_to_percent(ctx)
        LOGGER.warning("Cover %s: unknown no_sun_behavior %r", ctx.config.entity_id, behavior)
        return False

    async def _no_sun_open(self, ctx: CoverContext) -> bool:
        """No-sun behavior: raise cover to fully open position."""
        state = ctx.hass.states.get(ctx.config.entity_id)
        current_position: int | None = None
        if state is not None:
            raw = state.attributes.get(ATTR_CURRENT_POSITION)
            with contextlib.suppress(ValueError, TypeError):
                current_position = int(raw) if raw is not None else None

        if current_position is not None and abs(current_position - 100) <= self.POSITION_TOLERANCE_PERCENT:
            return True

        LOGGER.debug("Cover %s: no sun — raising to 100%%", ctx.config.entity_id)
        await ctx.hass.services.async_call(
            "cover",
            SERVICE_SET_COVER_POSITION,
            {ATTR_ENTITY_ID: ctx.config.entity_id, "position": 100},
            blocking=True,
        )
        await self._wait_for_position(ctx, 100)
        return True

    async def _no_sun_close(self, ctx: CoverContext) -> bool:
        """No-sun behavior: close slats to effective minimum tilt."""
        tilt = max(0.0, self._effective_min_tilt(ctx.config))
        LOGGER.debug("Cover %s: no sun — closing slats to %.1f%%", ctx.config.entity_id, tilt)
        await ctx.hass.services.async_call(
            "cover",
            SERVICE_SET_COVER_TILT_POSITION,
            {ATTR_ENTITY_ID: ctx.config.entity_id, "tilt_position": int(round(tilt))},
            blocking=True,
        )
        return True

    async def _no_sun_set_to_percent(self, ctx: CoverContext) -> bool:
        """No-sun behavior: set tilt to configured no_sun_position."""
        tilt = max(float(ctx.config.no_sun_position), self._effective_min_tilt(ctx.config))
        LOGGER.debug("Cover %s: no sun — setting tilt to %.1f%%", ctx.config.entity_id, tilt)
        await ctx.hass.services.async_call(
            "cover",
            SERVICE_SET_COVER_TILT_POSITION,
            {ATTR_ENTITY_ID: ctx.config.entity_id, "tilt_position": int(round(tilt))},
            blocking=True,
        )
        return True

    @staticmethod
    def _effective_min_tilt(config: CoverConfig) -> float:
        """Minimum tilt the integration may set."""
        base = float(config.manual_close_threshold) if config.respect_manual_close else 0.0
        angle_floor = 100.0 * (1.0 - config.max_angle / 90.0) if config.max_angle < 90 else 0.0
        return max(base, float(config.min_tilt_percent), angle_floor)

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
                    return True
            await asyncio.sleep(interval)
            elapsed += interval

        LOGGER.warning(
            "Timeout waiting for %s to reach position %d%%",
            ctx.config.entity_id,
            target_position,
        )
        return False
