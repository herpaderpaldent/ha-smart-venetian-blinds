"""
Seasonal pause binary sensor for smart_venetian_blinds.

Reports whether the window group is currently outside its configured season and
therefore not driving covers.
"""

from __future__ import annotations

from typing import Any

from custom_components.smart_venetian_blinds.coordinator import SmartVenetianBlindsDataUpdateCoordinator
from custom_components.smart_venetian_blinds.entity import SmartVenetianBlindsEntity
from custom_components.smart_venetian_blinds.season import SeasonWindow
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.const import EntityCategory
import homeassistant.util.dt as dt_util

SEASONAL_PAUSE_DESCRIPTION = BinarySensorEntityDescription(
    key="seasonal_pause",
    translation_key="seasonal_pause",
    entity_category=EntityCategory.DIAGNOSTIC,
    icon="mdi:calendar-remove",
)


class SeasonalPauseBinarySensor(SmartVenetianBlindsEntity, BinarySensorEntity):
    """
    Binary sensor reporting the seasonal pause state of a window group.

    ``on`` means the current date is outside the configured season, so the group
    keeps calculating sun position but no longer moves any covers.
    """

    def __init__(
        self,
        coordinator: SmartVenetianBlindsDataUpdateCoordinator,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, SEASONAL_PAUSE_DESCRIPTION, platform="binary_sensor")

    @property
    def _season(self) -> SeasonWindow:
        """Return the season window from the current entry options."""
        return SeasonWindow.from_options(self.coordinator.config_entry.options)

    @property
    def is_on(self) -> bool:
        """Return True if the group is currently seasonally paused."""
        return self._season.is_paused(dt_util.now().date())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the configured season window for use in dashboards and automations."""
        season = self._season
        return {
            "season_pause_enabled": season.enabled,
            "season_start": season.start_value,
            "season_end": season.end_value,
            "rest_position": season.rest_position,
        }


__all__ = [
    "SEASONAL_PAUSE_DESCRIPTION",
    "SeasonalPauseBinarySensor",
]
