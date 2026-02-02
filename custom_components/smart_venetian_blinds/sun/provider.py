# sun/provider.py
"""Provider for sun position data from Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import SUN_ENTITY
from custom_components.smart_venetian_blinds.sun.math import SunPosition
from homeassistant.core import callback

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class SunDataProvider:
    """Provides sun position data from Home Assistant states."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the provider."""
        self._hass = hass

    @callback
    def get_sun_position(self) -> SunPosition | None:
        """
        Get current sun position from the built-in sun.sun entity.

        Returns:
            SunPosition or None if data unavailable.
        """
        sun_state = self._hass.states.get(SUN_ENTITY)
        if not sun_state:
            return None

        # Get attributes with defaults
        azimuth = sun_state.attributes.get("azimuth", 0.0)
        elevation = sun_state.attributes.get("elevation", 0.0)

        try:
            return SunPosition(azimuth_deg=float(azimuth), elevation_deg=float(elevation))
        except (ValueError, TypeError):
            return None

    def get_tracked_entities(self) -> list[str]:
        """Get list of entity IDs to track for sun position updates."""
        return [SUN_ENTITY]

    @property
    def is_available(self) -> bool:
        """Return True if sun position data is available."""
        return self.get_sun_position() is not None
