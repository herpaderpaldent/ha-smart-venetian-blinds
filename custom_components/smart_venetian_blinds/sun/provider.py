# sun/provider.py
"""Provider for sun position data from Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import SENSOR_SUN_AZIMUTH, SENSOR_SUN_ELEVATION, SUN_ENTITY
from custom_components.smart_venetian_blinds.sun.math import SunPosition
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
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
        Get current sun position from HA states.

        Prefers dedicated sensors if available, falls back to sun.sun attributes.

        Returns:
            SunPosition or None if data unavailable.
        """
        # Try sensors first
        result = self._get_from_sensors()
        if result is not None:
            return result

        # Fallback to sun.sun entity
        return self._get_from_sun_entity()

    def _get_from_sensors(self) -> SunPosition | None:
        """Get sun position from dedicated sensor entities."""
        azimuth_state = self._hass.states.get(SENSOR_SUN_AZIMUTH)
        elevation_state = self._hass.states.get(SENSOR_SUN_ELEVATION)

        # Both sensors must be present
        if not azimuth_state or not elevation_state:
            return None

        # Both must have valid states
        if azimuth_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        if elevation_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None

        try:
            azimuth = float(azimuth_state.state)
            elevation = float(elevation_state.state)
            return SunPosition(azimuth_deg=azimuth, elevation_deg=elevation)
        except (ValueError, TypeError):
            return None

    def _get_from_sun_entity(self) -> SunPosition | None:
        """Get sun position from sun.sun entity attributes."""
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
        # Only return both sensors if BOTH are present
        azimuth_exists = self._hass.states.get(SENSOR_SUN_AZIMUTH) is not None
        elevation_exists = self._hass.states.get(SENSOR_SUN_ELEVATION) is not None

        if azimuth_exists and elevation_exists:
            return [SENSOR_SUN_AZIMUTH, SENSOR_SUN_ELEVATION]

        # Fallback to sun.sun if not both sensors present
        return [SUN_ENTITY]

    @property
    def is_available(self) -> bool:
        """Return True if sun position data is available."""
        return self.get_sun_position() is not None
