"""
Auto control switch for smart_venetian_blinds.

Allows enabling/disabling automatic control per window group.
"""

from __future__ import annotations

from typing import Any

from custom_components.smart_venetian_blinds.coordinator import SmartVenetianBlindsDataUpdateCoordinator
from custom_components.smart_venetian_blinds.entity import SmartVenetianBlindsEntity
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription

AUTO_CONTROL_DESCRIPTION = SwitchEntityDescription(
    key="auto_control",
    translation_key="auto_control",
    icon="mdi:auto-mode",
)


class AutoControlSwitch(SmartVenetianBlindsEntity, SwitchEntity):
    """
    Switch to enable/disable automatic blind control.

    When disabled, the integration will not automatically adjust blinds
    based on sun position changes.
    """

    def __init__(
        self,
        coordinator: SmartVenetianBlindsDataUpdateCoordinator,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, AUTO_CONTROL_DESCRIPTION, platform="switch")

    @property
    def is_on(self) -> bool:
        """Return True if auto control is enabled."""
        return self.coordinator.config_entry.runtime_data.auto_control_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable auto control and immediately re-apply cover positions."""
        runtime_data = self.coordinator.config_entry.runtime_data
        runtime_data.state.reset_for_fresh_start()
        runtime_data.auto_control_enabled = True
        self.async_write_ha_state()
        self.coordinator.trigger_update()
        if runtime_data.apply_cover_tilts is not None:
            await runtime_data.apply_cover_tilts()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable auto control."""
        self.coordinator.config_entry.runtime_data.auto_control_enabled = False
        self.async_write_ha_state()


__all__ = [
    "AUTO_CONTROL_DESCRIPTION",
    "AutoControlSwitch",
]
