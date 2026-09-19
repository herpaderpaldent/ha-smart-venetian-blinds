"""
Slat geometry number entities for smart_venetian_blinds.

Provides editable number entities for:
- Slat width (mm)
- Slat spacing (mm)
"""

from __future__ import annotations

from custom_components.smart_venetian_blinds.const import (
    CONF_SLAT_SPACING,
    CONF_SLAT_WIDTH,
    DEFAULT_SLAT_SPACING,
    DEFAULT_SLAT_WIDTH,
)
from custom_components.smart_venetian_blinds.coordinator import SmartVenetianBlindsDataUpdateCoordinator
from custom_components.smart_venetian_blinds.entity import SmartVenetianBlindsEntity
from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import EntityCategory, UnitOfLength

SLAT_WIDTH_DESCRIPTION = NumberEntityDescription(
    key="slat_width",
    translation_key="slat_width",
    native_unit_of_measurement=UnitOfLength.MILLIMETERS,
    device_class=NumberDeviceClass.DISTANCE,
    native_min_value=10,
    native_max_value=500,
    native_step=1,
    mode=NumberMode.BOX,
    entity_category=EntityCategory.CONFIG,
    icon="mdi:arrow-left-right",
)

SLAT_SPACING_DESCRIPTION = NumberEntityDescription(
    key="slat_spacing",
    translation_key="slat_spacing",
    native_unit_of_measurement=UnitOfLength.MILLIMETERS,
    device_class=NumberDeviceClass.DISTANCE,
    native_min_value=10,
    native_max_value=500,
    native_step=1,
    mode=NumberMode.BOX,
    entity_category=EntityCategory.CONFIG,
    icon="mdi:arrow-up-down",
)


class SlatWidthNumber(SmartVenetianBlindsEntity, NumberEntity):
    """Number entity for slat width configuration."""

    def __init__(self, coordinator: SmartVenetianBlindsDataUpdateCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, SLAT_WIDTH_DESCRIPTION, platform="number")

    @property
    def native_value(self) -> float:
        """Return the current slat width."""
        return self.coordinator.config_entry.data.get(CONF_SLAT_WIDTH, DEFAULT_SLAT_WIDTH)

    async def async_set_native_value(self, value: float) -> None:
        """Update slat width and recalculate."""
        entry = self.coordinator.config_entry
        self.hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_SLAT_WIDTH: int(value)},
        )
        self.coordinator.trigger_update()


class SlatSpacingNumber(SmartVenetianBlindsEntity, NumberEntity):
    """Number entity for slat spacing configuration."""

    def __init__(self, coordinator: SmartVenetianBlindsDataUpdateCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, SLAT_SPACING_DESCRIPTION, platform="number")

    @property
    def native_value(self) -> float:
        """Return the current slat spacing."""
        return self.coordinator.config_entry.data.get(CONF_SLAT_SPACING, DEFAULT_SLAT_SPACING)

    async def async_set_native_value(self, value: float) -> None:
        """Update slat spacing and recalculate."""
        entry = self.coordinator.config_entry
        self.hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_SLAT_SPACING: int(value)},
        )
        self.coordinator.trigger_update()


__all__ = [
    "SLAT_SPACING_DESCRIPTION",
    "SLAT_WIDTH_DESCRIPTION",
    "SlatSpacingNumber",
    "SlatWidthNumber",
]
