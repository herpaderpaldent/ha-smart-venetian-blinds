"""
Shared cover position helpers for the cover control pipeline.

Reading ``current_position`` off a cover state and waiting for a cover to arrive
at a target position are needed by several pipes. They are plain functions rather
than a base class or mixin on purpose: the pipes are structurally typed against
the ``CoverPipe`` protocol and share no ancestor, and the pipes that never touch
a position (``TiltPipe``, ``EnabledPipe``) should not inherit machinery they do
not use.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER
from homeassistant.components.cover import ATTR_CURRENT_POSITION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

POSITION_TOLERANCE_PERCENT = 2
"""How far a cover may sit from a target position and still count as arrived."""

_POLL_INTERVAL_SEC = 0.5


def read_position(hass: HomeAssistant, entity_id: str) -> int | None:
    """
    Read a cover's current position.

    Args:
        hass: The Home Assistant instance.
        entity_id: The cover entity to read.

    Returns:
        The position in percent, or None if the cover is unavailable, reports no
        position, or reports one that is not a number.
    """
    state = hass.states.get(entity_id)
    if state is None:
        return None

    raw_position = state.attributes.get(ATTR_CURRENT_POSITION)
    if raw_position is None:
        return None

    try:
        return int(raw_position)
    except (ValueError, TypeError):
        return None


def is_at_position(position: int | None, target: int) -> bool:
    """
    Return True if a position is within tolerance of the target.

    Args:
        position: The position to check, typically from :func:`read_position`.
            An unknown position never counts as arrived.
        target: The target position in percent.
    """
    return position is not None and abs(position - target) <= POSITION_TOLERANCE_PERCENT


async def async_wait_for_position(
    hass: HomeAssistant,
    entity_id: str,
    target: int,
    timeout_sec: float,
    *,
    label: str = "position",
) -> bool:
    """
    Poll a cover until it reaches the target position.

    Args:
        hass: The Home Assistant instance.
        entity_id: The cover entity to watch.
        target: The target position in percent.
        timeout_sec: How long to wait before giving up.
        label: What the target is called in the log messages, e.g.
            ``"season rest position"``.

    Returns:
        True if the cover reported the target position within the timeout,
        False on timeout.
    """
    elapsed = 0.0

    while elapsed < timeout_sec:
        current = read_position(hass, entity_id)
        if is_at_position(current, target):
            LOGGER.debug("Cover %s reached %s %d%%", entity_id, label, current)
            return True
        await asyncio.sleep(_POLL_INTERVAL_SEC)
        elapsed += _POLL_INTERVAL_SEC

    LOGGER.warning("Timeout waiting for %s to reach %s %d%%", entity_id, label, target)
    return False


__all__ = [
    "POSITION_TOLERANCE_PERCENT",
    "async_wait_for_position",
    "is_at_position",
    "read_position",
]
