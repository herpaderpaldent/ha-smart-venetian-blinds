"""Number platform for smart_venetian_blinds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import PARALLEL_UPDATES as PARALLEL_UPDATES

from .geometry_numbers import SlatSpacingNumber, SlatWidthNumber

if TYPE_CHECKING:
    from custom_components.smart_venetian_blinds.data import SmartVenetianBlindsConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartVenetianBlindsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    coordinator = entry.runtime_data.coordinator

    async_add_entities(
        [
            SlatWidthNumber(coordinator),
            SlatSpacingNumber(coordinator),
        ]
    )
