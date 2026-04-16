"""
Cover controller for smart_venetian_blinds.

Implements the cover control pipeline: a chain of responsibility that drives
covers to their target position and applies the calculated slat angle.
"""

from __future__ import annotations

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
from custom_components.smart_venetian_blinds.cover_control.context import CoverContext, CoverTrackingState
from custom_components.smart_venetian_blinds.cover_control.pipes import (
    EnabledPipe,
    ExitDetectionPipe,
    ExitPausedCheckPipe,
    NoSunPipe,
    PositionDrivePipe,
    SleepProtectionPipe,
    TiltPipe,
)

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


class Pipeline:
    """
    Cover control pipeline (chain of responsibility).

    Each pipe receives a CoverContext and either short-circuits (returning a bool)
    or passes control to the next pipe via call_next(). Pipes are called in order.
    """

    def __init__(
        self,
        pipes: list[
            EnabledPipe
            | SleepProtectionPipe
            | ExitPausedCheckPipe
            | NoSunPipe
            | ExitDetectionPipe
            | PositionDrivePipe
            | TiltPipe
        ],
    ) -> None:
        """Initialize with an ordered list of pipes."""
        self._pipes = pipes

    async def run(self, ctx: CoverContext) -> bool:
        """Run the pipeline against the given context."""

        async def call(index: int) -> bool:
            if index >= len(self._pipes):
                return False
            pipe = self._pipes[index]

            async def call_next() -> bool:
                return await call(index + 1)

            return await pipe.handle(ctx, call_next)

        return await call(0)


class CoverController:
    """
    Controller for applying tilt to covers.

    Runs each cover through a pipeline of pipes that implement the drive-then-tilt
    sequence with sleep protection, exit-pause detection, no-sun handling, and
    per-cover angle constraints.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        position_timeout_sec: int = DEFAULT_POSITION_TIMEOUT,
        settling_delay_sec: int = 5,
        cover_states: dict[str, CoverTrackingState] | None = None,
    ) -> None:
        """Initialize the cover controller."""
        self._hass = hass
        self._position_timeout_sec = position_timeout_sec
        self._settling_delay_sec = settling_delay_sec
        self._cover_states = cover_states if cover_states is not None else {}

    def _get_or_create_state(self, entity_id: str) -> CoverTrackingState:
        """Get or create the tracking state for a cover."""
        if entity_id not in self._cover_states:
            self._cover_states[entity_id] = CoverTrackingState()
        return self._cover_states[entity_id]

    def _build_pipeline(self) -> Pipeline:
        """Build the cover control pipeline."""
        return Pipeline(
            [
                EnabledPipe(),
                NoSunPipe(self._position_timeout_sec),
                SleepProtectionPipe(),
                ExitPausedCheckPipe(),
                ExitDetectionPipe(),
                PositionDrivePipe(self._position_timeout_sec, self._settling_delay_sec),
                TiltPipe(),
            ]
        )

    async def apply_calculation(
        self,
        config: CoverConfig,
        calculation: SlatCalculationResult | None,
    ) -> bool:
        """
        Apply calculated tilt to a cover via the control pipeline.

        Args:
            config: The cover configuration.
            calculation: The slat calculation result (None if sun below horizon).

        Returns:
            True if an action was taken, False if skipped.
        """
        state = self._get_or_create_state(config.entity_id)
        ctx = CoverContext(
            config=config,
            calculation=calculation,
            hass=self._hass,
            state=state,
        )
        pipeline = self._build_pipeline()
        return await pipeline.run(ctx)

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
            Dictionary mapping entity_id to whether an action was taken.
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
