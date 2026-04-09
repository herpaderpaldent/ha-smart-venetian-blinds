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
    CONF_MANUAL_OPEN_THRESHOLD,
    CONF_MAX_ANGLE,
    CONF_MIN_ANGLE,
    CONF_MIN_TILT_PERCENT,
    CONF_MINIMUM_TILT_CHANGE,
    CONF_NO_SUN_BEHAVIOR,
    CONF_NO_SUN_POSITION,
    CONF_OBSTACLE_ELEVATION_DEG,
    CONF_REFLECTION_PROTECTION_ENABLED,
    CONF_REFLECTION_PROTECTION_END_TIME,
    CONF_REFLECTION_PROTECTION_MIN_TILT,
    CONF_REFLECTION_PROTECTION_START_TIME,
    CONF_RESPECT_MANUAL_CLOSE,
    CONF_RESPECT_MANUAL_OPEN,
    DEFAULT_COVER_ENABLED,
    DEFAULT_DRIVE_POSITION,
    DEFAULT_INVERT_TILT,
    DEFAULT_MANUAL_CLOSE_THRESHOLD,
    DEFAULT_MANUAL_OPEN_THRESHOLD,
    DEFAULT_MAX_ANGLE,
    DEFAULT_MIN_ANGLE,
    DEFAULT_MIN_TILT_PERCENT,
    DEFAULT_MINIMUM_TILT_CHANGE,
    DEFAULT_NO_SUN_BEHAVIOR,
    DEFAULT_NO_SUN_POSITION,
    DEFAULT_OBSTACLE_ELEVATION_DEG,
    DEFAULT_POSITION_TIMEOUT,
    DEFAULT_REFLECTION_PROTECTION_ENABLED,
    DEFAULT_REFLECTION_PROTECTION_END_TIME,
    DEFAULT_REFLECTION_PROTECTION_MIN_TILT,
    DEFAULT_REFLECTION_PROTECTION_START_TIME,
    DEFAULT_RESPECT_MANUAL_CLOSE,
    DEFAULT_RESPECT_MANUAL_OPEN,
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
    minimum_tilt_change: int
    enabled: bool
    reflection_protection_enabled: bool
    reflection_protection_min_tilt: int
    reflection_protection_start_time: str
    reflection_protection_end_time: str
    min_tilt_percent: int = 0
    respect_manual_open: bool = True
    manual_open_threshold: int = 90
    obstacle_elevation_deg: float = DEFAULT_OBSTACLE_ELEVATION_DEG

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
            respect_manual_open=data.get(CONF_RESPECT_MANUAL_OPEN, DEFAULT_RESPECT_MANUAL_OPEN),
            manual_open_threshold=data.get(CONF_MANUAL_OPEN_THRESHOLD, DEFAULT_MANUAL_OPEN_THRESHOLD),
            minimum_tilt_change=data.get(CONF_MINIMUM_TILT_CHANGE, DEFAULT_MINIMUM_TILT_CHANGE),
            enabled=data.get(CONF_COVER_ENABLED, DEFAULT_COVER_ENABLED),
            reflection_protection_enabled=data.get(
                CONF_REFLECTION_PROTECTION_ENABLED, DEFAULT_REFLECTION_PROTECTION_ENABLED
            ),
            reflection_protection_min_tilt=data.get(
                CONF_REFLECTION_PROTECTION_MIN_TILT, DEFAULT_REFLECTION_PROTECTION_MIN_TILT
            ),
            reflection_protection_start_time=data.get(
                CONF_REFLECTION_PROTECTION_START_TIME, DEFAULT_REFLECTION_PROTECTION_START_TIME
            ),
            reflection_protection_end_time=data.get(
                CONF_REFLECTION_PROTECTION_END_TIME, DEFAULT_REFLECTION_PROTECTION_END_TIME
            ),
            min_tilt_percent=data.get(CONF_MIN_TILT_PERCENT, DEFAULT_MIN_TILT_PERCENT),
            obstacle_elevation_deg=data.get(CONF_OBSTACLE_ELEVATION_DEG, DEFAULT_OBSTACLE_ELEVATION_DEG),
        )


class CoverController:
    """
    Controller for applying tilt to covers.

    Implements the drive-then-tilt control sequence with:
    - Manual close detection (respects user closing blinds)
    - Position-based waiting
    - Tilt inversion support
    """

    # Position tolerance — class-level constant (not user-configurable)
    POSITION_TOLERANCE_PERCENT = 2

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        sun_has_hit_facade: bool = False,
        first_facade_hit_this_cycle: bool = False,
        position_timeout_sec: int = DEFAULT_POSITION_TIMEOUT,
    ) -> None:
        """Initialize the cover controller."""
        self._hass = hass
        self._sun_has_hit_facade = sun_has_hit_facade
        self._first_facade_hit_this_cycle = first_facade_hit_this_cycle
        self._position_timeout_sec = position_timeout_sec

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

        # If sun elevation is below cover's obstacle horizon, treat as no-sun
        if config.obstacle_elevation_deg > 0 and calculation.sun_elevation_deg <= config.obstacle_elevation_deg:
            LOGGER.debug(
                "Cover %s: sun elevation %.1f° is below obstacle angle %.1f°, applying no-sun behaviour",
                config.entity_id,
                calculation.sun_elevation_deg,
                config.obstacle_elevation_deg,
            )
            return await self._handle_no_sun(config)

        # Get current cover position
        current_position = self._get_cover_position(config.entity_id)
        if current_position is None:
            LOGGER.warning(
                "Cannot get position for %s, skipping",
                config.entity_id,
            )
            return False

        # Check manual close threshold (based on TILT, not position).
        # The invariant: the integration never sets tilt below this threshold (see _effective_min_tilt),
        # so any tilt below it was put there by the user.
        if config.respect_manual_close:
            current_tilt = self._get_cover_tilt(config.entity_id)
            if current_tilt is not None and current_tilt < config.manual_close_threshold:
                LOGGER.debug(
                    "Cover %s tilt at %.1f%% (below threshold %d%%), respecting manual close",
                    config.entity_id,
                    current_tilt,
                    config.manual_close_threshold,
                )
                return False

        # Check manual open threshold (based on POSITION, not tilt).
        # If the cover was raised above the threshold by the user (e.g. to step out through
        # a patio door), skip auto-control until the cover is lowered again.
        # Exception: on the very first facade hit of the solar day (is_first_facade_hit=True),
        # skip this check so that covers raised overnight by no_sun_behavior="open" are driven
        # back to their working position at sunrise.
        if (
            config.respect_manual_open
            and not self._first_facade_hit_this_cycle
            and current_position >= config.manual_open_threshold
        ):
            LOGGER.debug(
                "Cover %s position at %d%% (at or above threshold %d%%), respecting manual open",
                config.entity_id,
                current_position,
                config.manual_open_threshold,
            )
            return False

        # Drive to position if needed
        if abs(current_position - config.drive_position) > self.POSITION_TOLERANCE_PERCENT:
            LOGGER.debug(
                "Driving %s from %d%% to %d%%",
                config.entity_id,
                current_position,
                config.drive_position,
            )
            await self._set_cover_position(config.entity_id, config.drive_position)
            await self._wait_for_position(config.entity_id, config.drive_position)

        # Calculate target tilt
        tilt_percent = apply_tilt_inversion(
            calculation.slat_tilt_percent,
            config.invert_tilt,
        )
        # Never set below our own threshold — preserves the manual-close invariant
        tilt_percent = max(tilt_percent, self._effective_min_tilt(config))

        # Check if tilt change is significant enough
        current_tilt = self._get_cover_tilt(config.entity_id)
        if current_tilt is not None:
            tilt_change = abs(tilt_percent - current_tilt)
            if tilt_change < config.minimum_tilt_change:
                LOGGER.debug(
                    "Cover %s tilt change %.1f%% is below threshold %d%%, skipping",
                    config.entity_id,
                    tilt_change,
                    config.minimum_tilt_change,
                )
                return False

        LOGGER.debug(
            "Setting tilt for %s to %.1f%% (angle: %.1f°, inverted: %s)",
            config.entity_id,
            tilt_percent,
            calculation.slat_angle_deg,
            config.invert_tilt,
        )

        await self._set_cover_tilt(config.entity_id, tilt_percent)
        return True

    def _effective_min_tilt(self, config: CoverConfig) -> float:
        """Minimum tilt the integration may set (preserves manual-close invariant)."""
        base = float(config.manual_close_threshold) if config.respect_manual_close else 0.0
        return max(base, float(config.min_tilt_percent))

    def _is_reflection_protection_active(self, config: CoverConfig) -> bool:
        """
        Check if reflection protection should be active now.

        Reflection protection activates automatically when the sun has previously
        hit the facade during this solar cycle and is now no longer requiring blocking.
        It deactivates when the sun sets below the horizon (resetting sun_has_hit_facade).

        Args:
            config: The cover configuration.

        Returns:
            True if reflection protection is enabled and sun has hit facade this cycle.
        """
        if not config.reflection_protection_enabled:
            return False

        return self._sun_has_hit_facade

    async def _handle_no_sun(self, config: CoverConfig) -> bool:
        """
        Handle the case when sun is below horizon or behind facade.

        Args:
            config: The cover configuration.

        Returns:
            True if action was taken, False otherwise.
        """
        # Respect manual close even in the no-sun path.
        # If the user closed the slats manually, don't override them when the sun sets.
        if config.respect_manual_close:
            current_tilt = self._get_cover_tilt(config.entity_id)
            if current_tilt is not None and current_tilt < config.manual_close_threshold:
                LOGGER.debug(
                    "No sun: cover %s tilt at %.1f%% (below threshold %d%%), respecting manual close",
                    config.entity_id,
                    current_tilt,
                    config.manual_close_threshold,
                )
                return False

        # Respect manual open even in the no-sun path.
        # If the user raised the cover (e.g. to step outside), don't override that position
        # with a no-sun action such as "open to 100%".
        if config.respect_manual_open:
            current_position = self._get_cover_position(config.entity_id)
            if current_position is not None and current_position >= config.manual_open_threshold:
                LOGGER.debug(
                    "No sun: cover %s position at %d%% (at or above threshold %d%%), respecting manual open",
                    config.entity_id,
                    current_position,
                    config.manual_open_threshold,
                )
                return False

        # Check reflection protection first
        if self._is_reflection_protection_active(config):
            tilt = max(float(config.reflection_protection_min_tilt), self._effective_min_tilt(config))
            LOGGER.debug(
                "No sun + reflection protection active for %s, setting min tilt %d%%",
                config.entity_id,
                config.reflection_protection_min_tilt,
            )
            await self._set_cover_tilt(config.entity_id, tilt)
            return True

        behavior = config.no_sun_behavior

        if behavior == "keep_last":
            LOGGER.debug("No sun, keeping last position for %s", config.entity_id)
            return False

        if behavior == "open":
            current_position = self._get_cover_position(config.entity_id)
            if current_position is not None and abs(current_position - 100) > self.POSITION_TOLERANCE_PERCENT:
                LOGGER.debug("No sun, raising %s to 100%%", config.entity_id)
                await self._set_cover_position(config.entity_id, 100)
                await self._wait_for_position(config.entity_id, 100)
            return True

        if behavior == "close":
            tilt = max(0.0, self._effective_min_tilt(config))
            LOGGER.debug("No sun, closing %s", config.entity_id)
            await self._set_cover_tilt(config.entity_id, tilt)
            return True

        if behavior == "set_to_percent":
            tilt = max(float(config.no_sun_position), self._effective_min_tilt(config))
            LOGGER.debug(
                "No sun, setting %s to %d%%",
                config.entity_id,
                config.no_sun_position,
            )
            await self._set_cover_tilt(config.entity_id, tilt)
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

        while elapsed < self._position_timeout_sec:
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
