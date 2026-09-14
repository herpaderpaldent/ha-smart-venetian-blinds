"""
Seasonal pause binary sensor for smart_venetian_blinds.

Reports whether the window group is currently outside its configured season and
therefore not driving covers.
"""

from __future__ import annotations

from typing import Any

from custom_components.smart_venetian_blinds.const import ATTRIBUTION
from custom_components.smart_venetian_blinds.coordinator import SmartVenetianBlindsDataUpdateCoordinator
from custom_components.smart_venetian_blinds.entity_utils import create_window_group_device_info
from custom_components.smart_venetian_blinds.season import SeasonWindow
from custom_components.smart_venetian_blinds.utils.string_helpers import slugify_name
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

SEASONAL_PAUSE_DESCRIPTION = BinarySensorEntityDescription(
    key="seasonal_pause",
    translation_key="seasonal_pause",
    icon="mdi:calendar-remove",
)


class SeasonalPauseBinarySensor(CoordinatorEntity[SmartVenetianBlindsDataUpdateCoordinator], BinarySensorEntity):
    """
    Binary sensor reporting the seasonal pause state of a window group.

    ``on`` means the current date is outside the configured season, so the group
    keeps calculating sun position but no longer moves any covers.
    """

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description = SEASONAL_PAUSE_DESCRIPTION

    def __init__(
        self,
        coordinator: SmartVenetianBlindsDataUpdateCoordinator,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_seasonal_pause"
        self.entity_id = f"binary_sensor.{slugify_name(coordinator.config_entry.title)}_seasonal_pause"
        self._attr_device_info = create_window_group_device_info(coordinator.config_entry)

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
            "season_start": f"{season.start_day:02d}.{season.start_month:02d}",
            "season_end": f"{season.end_day:02d}.{season.end_month:02d}",
            "rest_position": season.rest_position,
        }


__all__ = [
    "SEASONAL_PAUSE_DESCRIPTION",
    "SeasonalPauseBinarySensor",
]
