"""
Slat calculation sensors for smart_venetian_blinds.

Provides sensors for:
- Slat angle (degrees)
- Slat tilt (percent)
- Profile angle (degrees, diagnostic)
"""

from __future__ import annotations

from custom_components.smart_venetian_blinds.const import ATTRIBUTION, DOMAIN
from custom_components.smart_venetian_blinds.coordinator import SmartVenetianBlindsDataUpdateCoordinator
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import DEGREE, PERCENTAGE
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

SLAT_ANGLE_DESCRIPTION = SensorEntityDescription(
    key="slat_angle",
    translation_key="slat_angle",
    native_unit_of_measurement=DEGREE,
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:angle-acute",
)

SLAT_TILT_DESCRIPTION = SensorEntityDescription(
    key="slat_tilt",
    translation_key="slat_tilt",
    native_unit_of_measurement=PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:blinds",
)

PROFILE_ANGLE_DESCRIPTION = SensorEntityDescription(
    key="profile_angle",
    translation_key="profile_angle",
    native_unit_of_measurement=DEGREE,
    state_class=SensorStateClass.MEASUREMENT,
    entity_registry_enabled_default=False,  # Diagnostic, disabled by default
    icon="mdi:angle-acute",
)


class SlatAngleSensor(CoordinatorEntity[SmartVenetianBlindsDataUpdateCoordinator], SensorEntity):
    """Sensor for calculated slat angle."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description = SLAT_ANGLE_DESCRIPTION

    def __init__(
        self,
        coordinator: SmartVenetianBlindsDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_slat_angle"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=coordinator.config_entry.title,
            manufacturer="Smart Venetian Blinds",
            model="Window Group",
        )

    @property
    def native_value(self) -> float | None:
        """Return the slat angle in degrees."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.slat_angle_deg


class SlatTiltSensor(CoordinatorEntity[SmartVenetianBlindsDataUpdateCoordinator], SensorEntity):
    """Sensor for calculated slat tilt percent."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description = SLAT_TILT_DESCRIPTION

    def __init__(
        self,
        coordinator: SmartVenetianBlindsDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_slat_tilt"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=coordinator.config_entry.title,
            manufacturer="Smart Venetian Blinds",
            model="Window Group",
        )

    @property
    def native_value(self) -> float | None:
        """Return the slat tilt percent."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.slat_tilt_percent


class ProfileAngleSensor(CoordinatorEntity[SmartVenetianBlindsDataUpdateCoordinator], SensorEntity):
    """Sensor for profile angle (diagnostic)."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    entity_description = PROFILE_ANGLE_DESCRIPTION

    def __init__(
        self,
        coordinator: SmartVenetianBlindsDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_profile_angle"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=coordinator.config_entry.title,
            manufacturer="Smart Venetian Blinds",
            model="Window Group",
        )

    @property
    def native_value(self) -> float | None:
        """Return the profile angle in degrees."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.profile_angle_deg


__all__ = [
    "PROFILE_ANGLE_DESCRIPTION",
    "SLAT_ANGLE_DESCRIPTION",
    "SLAT_TILT_DESCRIPTION",
    "ProfileAngleSensor",
    "SlatAngleSensor",
    "SlatTiltSensor",
]
