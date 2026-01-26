"""
Cover controller for smart_venetian_blinds.

Implements the drive-then-tilt control logic for venetian blinds.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from custom_components.smart_venetian_blinds.const import (
    CONF_COVER_ENABLED,
    CONF_COVER_ENTITY,
    CONF_DRIVE_POSITION,
    CONF_INVERT_TILT,
    CONF_MANUAL_CLOSE_THRESHOLD,
    CONF_MAX_ANGLE,
    CONF_MIN_ANGLE,
    CONF_NO_SUN_BEHAVIOR,
    CONF_NO_SUN_POSITION,
    CONF_RESPECT_MANUAL_CLOSE,
    CONF_TILT_ONLY_WHEN_DRIVEN,
    DEFAULT_COVER_ENABLED,
    DEFAULT_DRIVE_POSITION,
    DEFAULT_INVERT_TILT,
    DEFAULT_MANUAL_CLOSE_THRESHOLD,
    DEFAULT_MAX_ANGLE,
    DEFAULT_MIN_ANGLE,
    DEFAULT_NO_SUN_BEHAVIOR,
    DEFAULT_NO_SUN_POSITION,
    DEFAULT_RESPECT_MANUAL_CLOSE,
    DEFAULT_TILT_ONLY_WHEN_DRIVEN,
    LOGGER,
)
from custom_components.smart_venetian_blinds.sun.math import apply_tilt_inversion
from homeassistant.components.cover import ATTR_CURRENT_POSITION, ATTR_CURRENT_TILT_POSITION
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_SET_COVER_POSITION, SERVICE_SET_COVER_TILT_POSITION

if TYPE_CHECKING:
    from custom_components.smart_venetian_blinds.sun import SlatCalculationResult
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant


@dataclass
class CoverConfig:
    """Configuration for a single cover."""

    entity_id: str
    drive_position: int
    min_angle: int
    max_angle: int
    invert_tilt: bool
    no_sun_behavior: str
    no_sun_position: int
    respect_manual_close: bool
    manual_close_threshold: int
    tilt_only_when_driven: bool
    enabled: bool

    @classmethod
    def from_subentry(cls, subentry: ConfigSubentry) -> CoverConfig:
        """Create CoverConfig from a config subentry."""
        data = subentry.data
        return cls(
            entity_id=data[CONF_COVER_ENTITY],
            drive_position=data.get(CONF_DRIVE_POSITION, DEFAULT_DRIVE_POSITION),
            min_angle=data.get(CONF_MIN_ANGLE, DEFAULT_MIN_ANGLE),
            max_angle=data.get(CONF_MAX_ANGLE, DEFAULT_MAX_ANGLE),
            invert_tilt=data.get(CONF_INVERT_TILT, DEFAULT_INVERT_TILT),
            no_sun_behavior=data.get(CONF_NO_SUN_BEHAVIOR, DEFAULT_NO_SUN_BEHAVIOR),
            no_sun_position=data.get(CONF_NO_SUN_POSITION, DEFAULT_NO_SUN_POSITION),
            respect_manual_close=data.get(CONF_RESPECT_MANUAL_CLOSE, DEFAULT_RESPECT_MANUAL_CLOSE),
            manual_close_threshold=data.get(CONF_MANUAL_CLOSE_THRESHOLD, DEFAULT_MANUAL_CLOSE_THRESHOLD),
            tilt_only_when_driven=data.get(CONF_TILT_ONLY_WHEN_DRIVEN, DEFAULT_TILT_ONLY_WHEN_DRIVEN),
            enabled=data.get(CONF_COVER_ENABLED, DEFAULT_COVER_ENABLED),
        )


class CoverController:
    """
    Controller for applying tilt to covers.

    Implements the drive-then-tilt control sequence with:
    - Manual close detection (respects user closing blinds)
    - Position-based waiting
    - Tilt inversion support
    """

    # Timeouts and tolerances
    POSITION_TIMEOUT_SEC = 60
    POSITION_TOLERANCE_PERCENT = 2

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the cover controller."""
        self._hass = hass

    async def apply_calculation(
        self,
        config: CoverConfig,
        calculation: SlatCalculationResult | None,
    ) -> bool:
        """
        Apply calculated tilt to a cover.

        Implements the drive-then-tilt sequence:
        1. Check if cover is enabled
        2. Check manual close threshold
        3. Drive to position (if needed)
        4. Apply tilt

        Args:
            config: The cover configuration.
            calculation: The slat calculation result (None if sun below horizon).

        Returns:
            True if tilt was applied, False if skipped.
        """
        if not config.enabled:
            LOGGER.debug("Cover %s is disabled, skipping", config.entity_id)
            return False

        # Handle no-sun case
        if calculation is None or calculation.sun_is_behind_facade:
            return await self._handle_no_sun(config)

        # Get current cover position
        current_position = self._get_cover_position(config.entity_id)
        if current_position is None:
            LOGGER.warning(
                "Cannot get position for %s, skipping",
                config.entity_id,
            )
            return False

        # Check manual close threshold
        if config.respect_manual_close:
            if current_position < config.manual_close_threshold:
                LOGGER.debug(
                    "Cover %s at %d%% (below threshold %d%%), respecting manual close",
                    config.entity_id,
                    current_position,
                    config.manual_close_threshold,
                )
                return False

        # Drive to position if needed
        position_changed = False
        if abs(current_position - config.drive_position) > self.POSITION_TOLERANCE_PERCENT:
            LOGGER.debug(
                "Driving %s from %d%% to %d%%",
                config.entity_id,
                current_position,
                config.drive_position,
            )
            await self._set_cover_position(config.entity_id, config.drive_position)
            await self._wait_for_position(config.entity_id, config.drive_position)
            position_changed = True

        # Skip tilt if position didn't change and tilt_only_when_driven is set
        if config.tilt_only_when_driven and not position_changed:
            LOGGER.debug(
                "Cover %s position unchanged, tilt_only_when_driven is set, skipping tilt",
                config.entity_id,
            )
            return False

        # Calculate and apply tilt
        tilt_percent = apply_tilt_inversion(
            calculation.slat_tilt_percent,
            config.invert_tilt,
        )

        LOGGER.debug(
            "Setting tilt for %s to %.1f%% (angle: %.1f°, inverted: %s)",
            config.entity_id,
            tilt_percent,
            calculation.slat_angle_deg,
            config.invert_tilt,
        )

        await self._set_cover_tilt(config.entity_id, tilt_percent)
        return True

    async def _handle_no_sun(self, config: CoverConfig) -> bool:
        """
        Handle the case when sun is below horizon or behind facade.

        Args:
            config: The cover configuration.

        Returns:
            True if action was taken, False otherwise.
        """
        behavior = config.no_sun_behavior

        if behavior == "keep_last":
            LOGGER.debug("No sun, keeping last position for %s", config.entity_id)
            return False

        if behavior == "open":
            LOGGER.debug("No sun, opening %s", config.entity_id)
            await self._set_cover_tilt(config.entity_id, 100.0)
            return True

        if behavior == "close":
            LOGGER.debug("No sun, closing %s", config.entity_id)
            await self._set_cover_tilt(config.entity_id, 0.0)
            return True

        if behavior == "set_to_percent":
            LOGGER.debug(
                "No sun, setting %s to %d%%",
                config.entity_id,
                config.no_sun_position,
            )
            await self._set_cover_tilt(config.entity_id, float(config.no_sun_position))
            return True

        LOGGER.warning("Unknown no_sun_behavior: %s", behavior)
        return False

    def _get_cover_position(self, entity_id: str) -> int | None:
        """
        Get current position of a cover.

        Args:
            entity_id: The cover entity ID.

        Returns:
            Current position (0-100) or None if unavailable.
        """
        state = self._hass.states.get(entity_id)
        if state is None:
            return None

        position = state.attributes.get(ATTR_CURRENT_POSITION)
        if position is None:
            return None

        try:
            return int(position)
        except (ValueError, TypeError):
            return None

    def _get_cover_tilt(self, entity_id: str) -> float | None:
        """
        Get current tilt position of a cover.

        Args:
            entity_id: The cover entity ID.

        Returns:
            Current tilt (0-100) or None if unavailable.
        """
        state = self._hass.states.get(entity_id)
        if state is None:
            return None

        tilt = state.attributes.get(ATTR_CURRENT_TILT_POSITION)
        if tilt is None:
            return None

        try:
            return float(tilt)
        except (ValueError, TypeError):
            return None

    async def _set_cover_position(self, entity_id: str, position: int) -> None:
        """
        Set cover position.

        Args:
            entity_id: The cover entity ID.
            position: Target position (0-100).
        """
        await self._hass.services.async_call(
            "cover",
            SERVICE_SET_COVER_POSITION,
            {
                ATTR_ENTITY_ID: entity_id,
                "position": position,
            },
            blocking=True,
        )

    async def _set_cover_tilt(self, entity_id: str, tilt: float) -> None:
        """
        Set cover tilt position.

        Args:
            entity_id: The cover entity ID.
            tilt: Target tilt (0-100).
        """
        await self._hass.services.async_call(
            "cover",
            SERVICE_SET_COVER_TILT_POSITION,
            {
                ATTR_ENTITY_ID: entity_id,
                "tilt_position": int(round(tilt)),
            },
            blocking=True,
        )

    async def _wait_for_position(
        self,
        entity_id: str,
        target_position: int,
    ) -> bool:
        """
        Wait for cover to reach target position.

        Args:
            entity_id: The cover entity ID.
            target_position: Expected position when done.

        Returns:
            True if position was reached, False on timeout.
        """
        elapsed = 0.0
        interval = 0.5

        while elapsed < self.POSITION_TIMEOUT_SEC:
            current = self._get_cover_position(entity_id)
            if current is not None:
                if abs(current - target_position) <= self.POSITION_TOLERANCE_PERCENT:
                    LOGGER.debug(
                        "Cover %s reached position %d%%",
                        entity_id,
                        current,
                    )
                    return True

            await asyncio.sleep(interval)
            elapsed += interval

        LOGGER.warning(
            "Timeout waiting for %s to reach position %d%%",
            entity_id,
            target_position,
        )
        return False

    async def apply_to_all_covers(
        self,
        subentries: Any,
        calculation: SlatCalculationResult | None,
    ) -> dict[str, bool]:
        """
        Apply calculation to all covers in a group.

        Args:
            subentries: Dictionary of config subentries for covers.
            calculation: The slat calculation result.

        Returns:
            Dictionary mapping entity_id to whether tilt was applied.
        """
        results: dict[str, bool] = {}

        for subentry in subentries.values():
            config = CoverConfig.from_subentry(subentry)
            try:
                applied = await self.apply_calculation(config, calculation)
                results[config.entity_id] = applied
            except Exception:  # noqa: BLE001 - intentional broad catch for resilience
                LOGGER.exception("Error applying tilt to %s", config.entity_id)
                results[config.entity_id] = False

        return results
