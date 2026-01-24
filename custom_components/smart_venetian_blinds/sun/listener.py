"""
Sun state change listener for smart_venetian_blinds.

Listens for sun entity state changes and triggers updates with debouncing.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from custom_components.smart_venetian_blinds.const import LOGGER
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback


class SunStateListener:
    """
    Listener for sun entity state changes with debouncing.

    Monitors specified entity IDs for state changes and calls
    the provided callback after a debounce period.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entity_ids: list[str],
        update_callback: Callable[[], None],
        debounce_seconds: float = 1.0,
    ) -> None:
        """
        Initialize the sun state listener.

        Args:
            hass: The Home Assistant instance.
            entity_ids: List of entity IDs to track.
            update_callback: Callback to call when state changes.
            debounce_seconds: Seconds to debounce rapid state changes.
        """
        self._hass = hass
        self._entity_ids = set(entity_ids)
        self._callback = update_callback
        self._debounce_seconds = debounce_seconds
        self._debounce_task: asyncio.Task[None] | None = None
        self._unsubscribe: Callable[[], None] | None = None

    def start(self) -> None:
        """Start listening for state changes."""
        if self._unsubscribe is not None:
            return  # Already started

        from homeassistant.helpers.event import async_track_state_change_event  # noqa: PLC0415

        self._unsubscribe = async_track_state_change_event(
            self._hass,
            list(self._entity_ids),
            self._on_state_change,
        )

        LOGGER.debug("Started sun state listener for entities: %s", self._entity_ids)

    def stop(self) -> None:
        """Stop listening for state changes."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

        if self._debounce_task is not None:
            self._debounce_task.cancel()
            self._debounce_task = None

        LOGGER.debug("Stopped sun state listener")

    @callback
    def _on_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle state change event with debouncing."""
        new_state: State | None = event.data.get("new_state")
        old_state: State | None = event.data.get("old_state")

        # Ignore unavailable/unknown states
        if new_state is None or new_state.state in ("unavailable", "unknown"):
            return

        # Check if value actually changed (not just attribute updates)
        if old_state is not None:
            try:
                old_val = float(old_state.state)
                new_val = float(new_state.state)
                if abs(new_val - old_val) < 0.1:
                    return  # No significant change
            except (ValueError, TypeError):
                pass  # Non-numeric states, trigger update

        LOGGER.debug(
            "Sun state change detected: %s -> %s",
            old_state.state if old_state else "None",
            new_state.state,
        )

        # Cancel existing debounce task
        if self._debounce_task is not None:
            self._debounce_task.cancel()

        # Schedule debounced callback
        self._debounce_task = self._hass.async_create_task(
            self._debounced_callback(),
        )

    async def _debounced_callback(self) -> None:
        """Call the callback after debounce period."""
        await asyncio.sleep(self._debounce_seconds)
        self._callback()


__all__ = ["SunStateListener"]
