"""DrivingCheckPipe — skip pipeline when the cover is already in motion."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from custom_components.smart_venetian_blinds.cover_control.context import CoverContext

_DRIVING_STATES = frozenset({"opening", "closing"})


class DrivingCheckPipe:
    """
    Skip the pipeline when the cover is already in motion.

    If the cover's HA state is ``opening`` or ``closing`` at the start of a pipeline
    run, an external actor (user remote, wall switch, another automation) is driving
    it. Interfering with a tilt or position command would fight the user, so the
    entire pipeline is skipped for this cycle.

    This pipe intentionally runs **after** ``EnabledPipe`` and **before** everything
    else. It does not affect self-initiated movement: ``PositionDrivePipe`` drives
    the cover and waits (blocking) for it to reach its target before calling
    ``TiltPipe``, so within a single pipeline run the cover is always settled by the
    time any action reaches the user.
    """

    async def handle(self, ctx: CoverContext, call_next: Callable[[], Awaitable[bool]]) -> bool:
        """Handle pipe step."""
        state = ctx.hass.states.get(ctx.config.entity_id)
        if state is not None and state.state in _DRIVING_STATES:
            LOGGER.debug(
                "Cover %s is currently %s — skipping pipeline",
                ctx.config.entity_id,
                state.state,
            )
            return False

        return await call_next()
