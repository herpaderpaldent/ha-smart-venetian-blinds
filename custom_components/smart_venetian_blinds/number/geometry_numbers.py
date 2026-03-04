"""
Slat geometry number entities for smart_venetian_blinds.

Provides editable number entities for:
- Slat width (mm)
- Slat spacing (mm)
"""

from __future__ import annotations

from custom_components.smart_venetian_blinds.const import (
    ATTRIBUTION,
    CONF_SLAT_SPACING,
    CONF_SLAT_WIDTH,
    DEFAULT_SLAT_SPACING,
    DEFAULT_SLAT_WIDTH,
    DOMAIN,
)
from custom_components.smart_venetian_blinds.coordinator import SmartVenetianBlindsDataUpdateCoordinator
from custom_components.smart_venetian_blinds.utils.string_helpers import slugify_name
from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import EntityCategory, UnitOfLength
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
)


class SlatWidthNumber(CoordinatorEntity[SmartVenetianBlindsDataUpdateCoordinator], NumberEntity):
    """Number entity for slat width configuration."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description = SLAT_WIDTH_DESCRIPTION

    def __init__(self, coordinator: SmartVenetianBlindsDataUpdateCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_slat_width"
        self.entity_id = f"number.{slugify_name(coordinator.config_entry.title)}_slat_width"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=coordinator.config_entry.title,
            manufacturer="Smart Venetian Blinds",
            model="Window Group",
            entry_type=DeviceEntryType.SERVICE,
        )

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


class SlatSpacingNumber(CoordinatorEntity[SmartVenetianBlindsDataUpdateCoordinator], NumberEntity):
    """Number entity for slat spacing configuration."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description = SLAT_SPACING_DESCRIPTION

    def __init__(self, coordinator: SmartVenetianBlindsDataUpdateCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_slat_spacing"
        self.entity_id = f"number.{slugify_name(coordinator.config_entry.title)}_slat_spacing"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=coordinator.config_entry.title,
            manufacturer="Smart Venetian Blinds",
            model="Window Group",
            entry_type=DeviceEntryType.SERVICE,
        )

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
