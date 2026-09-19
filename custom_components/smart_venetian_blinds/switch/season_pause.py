"""
Seasonal pause switch for smart_venetian_blinds.

Turns the seasonal pause window on or off from the window group's device page.
"""

from __future__ import annotations

from typing import Any

from custom_components.smart_venetian_blinds.const import CONF_SEASON_PAUSE_ENABLED
from custom_components.smart_venetian_blinds.coordinator import SmartVenetianBlindsDataUpdateCoordinator
from custom_components.smart_venetian_blinds.entity import SmartVenetianBlindsEntity
from custom_components.smart_venetian_blinds.entity_utils import async_merge_entry_options
from custom_components.smart_venetian_blinds.season import SeasonWindow
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory

SEASON_PAUSE_DESCRIPTION = SwitchEntityDescription(
    key="season_pause",
    translation_key="season_pause",
    entity_category=EntityCategory.CONFIG,
    icon="mdi:calendar-sync",
)


class SeasonPauseSwitch(SmartVenetianBlindsEntity, SwitchEntity):
    """
    Switch enabling the seasonal pause window for a window group.

    When off, the group controls covers all year round. When on, the configured
    season applies and the group stops driving covers outside it.
    """

    def __init__(self, coordinator: SmartVenetianBlindsDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, SEASON_PAUSE_DESCRIPTION, platform="switch")

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
