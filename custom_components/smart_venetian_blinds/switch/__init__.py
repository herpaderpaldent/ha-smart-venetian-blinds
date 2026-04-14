"""Switch platform for smart_venetian_blinds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import PARALLEL_UPDATES as PARALLEL_UPDATES

from .auto_control import AutoControlSwitch
from .exit_mode import ExitModeSwitch

if TYPE_CHECKING:
    from custom_components.smart_venetian_blinds.data import SmartVenetianBlindsConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartVenetianBlindsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator = entry.runtime_data.coordinator

    entities: list[AutoControlSwitch | ExitModeSwitch] = [AutoControlSwitch(coordinator)]
    entities.extend(ExitModeSwitch(coordinator, subentry) for subentry in entry.subentries.values())

    async_add_entities(entities)
