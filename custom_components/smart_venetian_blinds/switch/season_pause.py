"""
Seasonal pause switch for smart_venetian_blinds.

Turns the seasonal pause window on or off from the window group's device page.
"""

from __future__ import annotations

from typing import Any

from custom_components.smart_venetian_blinds.const import ATTRIBUTION, CONF_SEASON_PAUSE_ENABLED
from custom_components.smart_venetian_blinds.coordinator import SmartVenetianBlindsDataUpdateCoordinator
from custom_components.smart_venetian_blinds.entity_utils import (
    async_merge_entry_options,
    build_entity_id,
    create_window_group_device_info,
)
from custom_components.smart_venetian_blinds.season import SeasonWindow
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

SEASON_PAUSE_DESCRIPTION = SwitchEntityDescription(
    key="season_pause",
    translation_key="season_pause",
    entity_category=EntityCategory.CONFIG,
    icon="mdi:calendar-sync",
)


class SeasonPauseSwitch(CoordinatorEntity[SmartVenetianBlindsDataUpdateCoordinator], SwitchEntity):
    """
    Switch enabling the seasonal pause window for a window group.

    When off, the group controls covers all year round. When on, the configured
    season applies and the group stops driving covers outside it.
    """

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description = SEASON_PAUSE_DESCRIPTION

    def __init__(self, coordinator: SmartVenetianBlindsDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_season_pause"
        self.entity_id = build_entity_id("switch", coordinator.config_entry.title, SEASON_PAUSE_DESCRIPTION.key)
        self._attr_device_info = create_window_group_device_info(coordinator.config_entry)

    @property
    def is_on(self) -> bool:
        """Return True if the seasonal pause window is enabled."""
        return SeasonWindow.from_options(self.coordinator.config_entry.options).enabled

    async def _async_set_enabled(self, enabled: bool) -> None:
        """Persist the new state; the entry reload applies it."""
        async_merge_entry_options(
            self.hass,
            self.coordinator.config_entry,
            **{CONF_SEASON_PAUSE_ENABLED: enabled},
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the seasonal pause window."""
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the seasonal pause window."""
        await self._async_set_enabled(False)


__all__ = [
    "SEASON_PAUSE_DESCRIPTION",
    "SeasonPauseSwitch",
]
