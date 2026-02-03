"""
Event-driven coordinator for smart_venetian_blinds.

This coordinator manages sun position tracking and slat angle calculations
for a window group. Instead of polling, it listens for sun entity state changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from custom_components.smart_venetian_blinds.const import (
    CONF_CHANGE_THRESHOLD,
    CONF_FACADE_AZIMUTH,
    CONF_MIN_UPDATE_INTERVAL,
    CONF_SAFETY_MARGIN,
    CONF_SLAT_SPACING,
    CONF_SLAT_WIDTH,
    DEFAULT_CHANGE_THRESHOLD,
    DEFAULT_MIN_UPDATE_INTERVAL,
    DEFAULT_SAFETY_MARGIN,
    LOGGER,
)
from custom_components.smart_venetian_blinds.sun import SlatCalculationResult, calculate_slat_angle
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

if TYPE_CHECKING:
    from custom_components.smart_venetian_blinds.data import SmartVenetianBlindsConfigEntry
    from custom_components.smart_venetian_blinds.sun import SunDataProvider
    from homeassistant.core import HomeAssistant


class SmartVenetianBlindsDataUpdateCoordinator(DataUpdateCoordinator[SlatCalculationResult | None]):
    """
    Event-driven coordinator for slat angle calculations.

    This coordinator:
    - Listens for sun position changes via state listeners
    - Calculates optimal slat angles based on group configuration
    - Throttles updates based on configured thresholds
    - Notifies entities when calculation results change

    Unlike a typical DataUpdateCoordinator, this one doesn't poll.
    Updates are triggered by sun entity state changes.
    """

    config_entry: SmartVenetianBlindsConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SmartVenetianBlindsConfigEntry,
        sun_provider: SunDataProvider,
    ) -> None:
        """
        Initialize the coordinator.

        Args:
            hass: The Home Assistant instance.
            config_entry: The config entry for this window group.
            sun_provider: Provider for sun position data.
        """
        super().__init__(
            hass,
            LOGGER,
            config_entry=config_entry,
            name=f"smart_venetian_blinds_{config_entry.entry_id}",
            update_interval=None,  # No polling - event-driven
        )
        self._sun_provider = sun_provider
        self._listener_started = False

    @property
    def sun_provider(self) -> SunDataProvider:
        """Get the sun data provider."""
        return self._sun_provider

    @property
    def change_threshold(self) -> int:
        """Get the configured change threshold in degrees."""
        return self.config_entry.options.get(
            CONF_CHANGE_THRESHOLD,
            DEFAULT_CHANGE_THRESHOLD,
        )

    @property
    def min_update_interval(self) -> int:
        """Get the configured minimum update interval in seconds."""
        return self.config_entry.options.get(
            CONF_MIN_UPDATE_INTERVAL,
            DEFAULT_MIN_UPDATE_INTERVAL,
        )

    async def _async_setup(self) -> None:
        """Set up the coordinator."""
        LOGGER.debug(
            "Coordinator setup for group: %s",
            self.config_entry.title,
        )

    async def _async_update_data(self) -> SlatCalculationResult | None:
        """
        Calculate slat angle based on current sun position.

        This is called when manually refreshing or on initial setup.
        Event-driven updates also trigger entity updates via async_set_updated_data.

        Returns:
            The calculation result or None if sun is below horizon.
        """
        return self._calculate_slat_angle()

    def _calculate_slat_angle(self) -> SlatCalculationResult | None:
        """
        Perform slat angle calculation for this window group.

        Returns:
            The calculation result or None if sun is below horizon.
        """
        sun_position = self._sun_provider.get_sun_position()
        if sun_position is None:
            LOGGER.debug("No sun position available")
            return None

        # Get group configuration
        facade_azimuth = self.config_entry.data.get(CONF_FACADE_AZIMUTH, 180)
        slat_width = self.config_entry.data.get(CONF_SLAT_WIDTH, 80)
        slat_spacing = self.config_entry.data.get(CONF_SLAT_SPACING, 70)
        safety_margin = self.config_entry.data.get(CONF_SAFETY_MARGIN, DEFAULT_SAFETY_MARGIN)

        # Calculate slat angle
        result = calculate_slat_angle(
            sun=sun_position,
            facade_azimuth_deg=facade_azimuth,
            slat_width_mm=slat_width,
            slat_spacing_mm=slat_spacing,
            safety_margin_deg=safety_margin,
        )

        LOGGER.debug(
            "Calculated slat angle for %s: %s",
            self.config_entry.title,
            result,
        )

        # Update sun_has_hit_facade tracking
        state = self.config_entry.runtime_data.state
        if result is None:
            # Sun below horizon: reset flag
            state.sun_has_hit_facade = False
        elif not result.sun_is_behind_facade:
            # Sun is on facade (even at angle 0°): mark as hit
            state.sun_has_hit_facade = True
            state.no_sun_action_applied = False
        # else: sun behind facade, leave unchanged (preserves True after sun passes)

        return result

    def trigger_update(self) -> None:
        """
        Trigger an update from sun state change.

        This is called by the SunStateListener when sun position changes.
        """
        result = self._calculate_slat_angle()

        # Update the coordinator's data and notify listeners
        self.async_set_updated_data(result)

    def should_apply_update(self, new_angle: float) -> bool:
        """
        Check if update should be applied based on throttling rules.

        Args:
            new_angle: The newly calculated slat angle.

        Returns:
            True if the update should be applied.
        """
        state = self.config_entry.runtime_data.state

        return state.should_apply(
            new_angle=new_angle,
            threshold_deg=self.change_threshold,
            min_interval_sec=self.min_update_interval,
        )

    def mark_update_applied(self, angle: float) -> None:
        """
        Mark that an update was applied.

        Args:
            angle: The angle that was applied.
        """
        self.config_entry.runtime_data.state.mark_applied(angle)

    def get_group_data(self) -> dict[str, Any]:
        """
        Get group configuration data for diagnostics.

        Returns:
            Dictionary of group configuration.
        """
        return {
            "title": self.config_entry.title,
            "facade_azimuth": self.config_entry.data.get(CONF_FACADE_AZIMUTH),
            "slat_width": self.config_entry.data.get(CONF_SLAT_WIDTH),
            "slat_spacing": self.config_entry.data.get(CONF_SLAT_SPACING),
            "change_threshold": self.change_threshold,
            "min_update_interval": self.min_update_interval,
            "covers_count": len(self.config_entry.subentries),
        }
