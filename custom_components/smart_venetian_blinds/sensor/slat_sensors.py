"""
Slat calculation sensors for smart_venetian_blinds.

Provides sensors for:
- Slat angle (degrees)
- Slat tilt (percent)
- Profile angle (degrees, diagnostic)
"""

from __future__ import annotations

from custom_components.smart_venetian_blinds.coordinator import SmartVenetianBlindsDataUpdateCoordinator
from custom_components.smart_venetian_blinds.entity import SmartVenetianBlindsEntity
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import DEGREE, PERCENTAGE

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


class SlatAngleSensor(SmartVenetianBlindsEntity, SensorEntity):
    """Sensor for calculated slat angle."""

    def __init__(
        self,
        coordinator: SmartVenetianBlindsDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, SLAT_ANGLE_DESCRIPTION, platform="sensor")

    @property
    def native_value(self) -> float | None:
        """Return the slat angle in degrees."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.slat_angle_deg


class SlatTiltSensor(SmartVenetianBlindsEntity, SensorEntity):
    """Sensor for calculated slat tilt percent."""

    def __init__(
        self,
        coordinator: SmartVenetianBlindsDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, SLAT_TILT_DESCRIPTION, platform="sensor")

    @property
    def native_value(self) -> float | None:
        """Return the slat tilt percent."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.slat_tilt_percent


class ProfileAngleSensor(SmartVenetianBlindsEntity, SensorEntity):
    """Sensor for profile angle (diagnostic)."""

    def __init__(
        self,
        coordinator: SmartVenetianBlindsDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, PROFILE_ANGLE_DESCRIPTION, platform="sensor")

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
