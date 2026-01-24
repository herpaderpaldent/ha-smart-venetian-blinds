"""
Sun data provider for smart_venetian_blinds.

Reads sun position from Home Assistant entities with fallback support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import LOGGER, SENSOR_SUN_AZIMUTH, SENSOR_SUN_ELEVATION, SUN_ENTITY
from custom_components.smart_venetian_blinds.sun.math import SunPosition

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class SunDataProvider:
    """
    Provides sun position data from Home Assistant entities.

    Supports two data sources with automatic fallback:
    1. Primary: sensor.sun_solar_azimuth + sensor.sun_solar_elevation
    2. Fallback: sun.sun entity attributes (azimuth, elevation)
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the sun data provider."""
        self._hass = hass

    def get_sun_position(self) -> SunPosition | None:
        """
        Get current sun position from available entities.

        Returns:
            SunPosition with azimuth and elevation, or None if unavailable.
        """
        # Try primary sensors first
        position = self._get_from_sensors()
        if position is not None:
            return position

        # Fallback to sun.sun entity
        return self._get_from_sun_entity()

    def _get_from_sensors(self) -> SunPosition | None:
        """Try to get sun position from dedicated sensors."""
        azimuth_state = self._hass.states.get(SENSOR_SUN_AZIMUTH)
        elevation_state = self._hass.states.get(SENSOR_SUN_ELEVATION)

        if azimuth_state is None or elevation_state is None:
            return None

        try:
            azimuth = float(azimuth_state.state)
            elevation = float(elevation_state.state)
            return SunPosition(azimuth_deg=azimuth, elevation_deg=elevation)
        except (ValueError, TypeError):
            LOGGER.debug(
                "Invalid sun sensor values: azimuth=%s, elevation=%s",
                azimuth_state.state,
                elevation_state.state,
            )
            return None

    def _get_from_sun_entity(self) -> SunPosition | None:
        """Get sun position from sun.sun entity attributes."""
        sun_state = self._hass.states.get(SUN_ENTITY)

        if sun_state is None:
            LOGGER.warning("No sun entity available")
            return None

        try:
            azimuth = float(sun_state.attributes.get("azimuth", 0))
            elevation = float(sun_state.attributes.get("elevation", 0))
            return SunPosition(azimuth_deg=azimuth, elevation_deg=elevation)
        except (ValueError, TypeError) as ex:
            LOGGER.debug("Invalid sun.sun attributes: %s", ex)
            return None

    def get_tracked_entities(self) -> list[str]:
        """
        Get list of entity IDs to track for state changes.

        Returns entities in priority order - if primary sensors exist,
        track those; otherwise track sun.sun.
        """
        azimuth_state = self._hass.states.get(SENSOR_SUN_AZIMUTH)
        elevation_state = self._hass.states.get(SENSOR_SUN_ELEVATION)

        if azimuth_state is not None and elevation_state is not None:
            return [SENSOR_SUN_AZIMUTH, SENSOR_SUN_ELEVATION]

        return [SUN_ENTITY]

    @property
    def is_available(self) -> bool:
        """Check if sun data is available."""
        return self.get_sun_position() is not None
