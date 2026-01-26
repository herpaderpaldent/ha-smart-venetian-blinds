"""Sensor platform for smart_venetian_blinds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import PARALLEL_UPDATES as PARALLEL_UPDATES

from .slat_sensors import ProfileAngleSensor, SlatAngleSensor, SlatTiltSensor

if TYPE_CHECKING:
    from custom_components.smart_venetian_blinds.data import SmartVenetianBlindsConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartVenetianBlindsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data.coordinator

    async_add_entities(
        [
            SlatAngleSensor(coordinator),
            SlatTiltSensor(coordinator),
            ProfileAngleSensor(coordinator),
        ]
    )
