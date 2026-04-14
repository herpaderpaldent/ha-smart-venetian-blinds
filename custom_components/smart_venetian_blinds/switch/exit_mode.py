"""
Exit mode switch for smart_venetian_blinds.

Allows enabling/disabling exit mode (daily pause) per individual cover.
When exit mode is ON, the cover is retracted to 100% and automatic
angle control is suspended for that cover until the switch is turned OFF.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.smart_venetian_blinds.const import ATTRIBUTION, CONF_COVER_ENTITY, CONF_COVER_NAME, LOGGER
from custom_components.smart_venetian_blinds.coordinator import SmartVenetianBlindsDataUpdateCoordinator
from custom_components.smart_venetian_blinds.cover_control.context import CoverTrackingState
from custom_components.smart_venetian_blinds.entity_utils import create_window_group_device_info
from custom_components.smart_venetian_blinds.utils.string_helpers import slugify_name
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_SET_COVER_POSITION
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry


EXIT_MODE_DESCRIPTION = SwitchEntityDescription(
    key="exit_paused",
    translation_key="exit_paused",
    icon="mdi:pause-circle-outline",
)


class ExitModeSwitch(CoordinatorEntity[SmartVenetianBlindsDataUpdateCoordinator], SwitchEntity):
    """
    Switch to enable/disable exit mode (daily pause) for a single cover.

    When turned ON: the cover is retracted to 100% and the pipeline stops
    applying automatic tilt until the switch is turned OFF again.

    When turned OFF: exit mode is cleared and the pipeline immediately
    drives the cover back to its calculated position and tilt.
    """

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description = EXIT_MODE_DESCRIPTION

    def __init__(
        self,
        coordinator: SmartVenetianBlindsDataUpdateCoordinator,
        subentry: ConfigSubentry,
    ) -> None:
        """Initialize the exit mode switch for a single cover."""
        super().__init__(coordinator)
        self._cover_entity_id: str = subentry.data[CONF_COVER_ENTITY]
        cover_name: str = subentry.data.get(CONF_COVER_NAME, self._cover_entity_id)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{subentry.subentry_id}_exit_paused"
        self.entity_id = f"switch.{slugify_name(cover_name)}_exit_paused"
        self._attr_device_info = create_window_group_device_info(entry)

    @property
    def is_on(self) -> bool:
        """Return True when exit mode is active for this cover."""
        cover_states = self.coordinator.config_entry.runtime_data.state.cover_states
        state = cover_states.get(self._cover_entity_id)
        return state.exit_paused if state is not None else False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate exit mode: pause pipeline and retract cover to 100%."""
        runtime_data = self.coordinator.config_entry.runtime_data
        cover_states = runtime_data.state.cover_states
        if self._cover_entity_id not in cover_states:
            cover_states[self._cover_entity_id] = CoverTrackingState()
        cover_states[self._cover_entity_id].exit_paused = True
        self.async_write_ha_state()
        LOGGER.debug("Exit mode activated for cover %s", self._cover_entity_id)
        await self.hass.services.async_call(
            "cover",
            SERVICE_SET_COVER_POSITION,
            {ATTR_ENTITY_ID: self._cover_entity_id, "position": 100},
            blocking=True,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate exit mode: resume pipeline and immediately apply tilt."""
        runtime_data = self.coordinator.config_entry.runtime_data
        cover_states = runtime_data.state.cover_states
        if self._cover_entity_id in cover_states:
            cover_states[self._cover_entity_id].exit_paused = False
        self.async_write_ha_state()
        LOGGER.debug("Exit mode deactivated for cover %s, resuming tracking", self._cover_entity_id)
        if runtime_data.apply_cover_tilts is not None:
            await runtime_data.apply_cover_tilts()


__all__ = [
    "EXIT_MODE_DESCRIPTION",
    "ExitModeSwitch",
]
