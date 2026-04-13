"""Tests for CoverController and cover control pipeline."""

# ruff: noqa: SLF001

from __future__ import annotations

import dataclasses
from unittest.mock import AsyncMock, MagicMock

import pytest

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
    DEFAULT_RESPECT_MANUAL_CLOSE,
    DEFAULT_RESPECT_MANUAL_OPEN,
)
from custom_components.smart_venetian_blinds.cover_control.context import CoverTrackingState
from custom_components.smart_venetian_blinds.cover_control.controller import CoverConfig, CoverController
from custom_components.smart_venetian_blinds.sun.math import SlatCalculationResult
from tests.conftest import create_mock_state


@pytest.mark.unit
class TestCoverConfigFromSubentry:
    """Tests for CoverConfig.from_subentry class method."""

    def test_all_fields_present(self) -> None:
        """Creates CoverConfig with all fields from subentry data."""
        subentry = MagicMock()
        subentry.data = {
            CONF_COVER_ENTITY: "cover.test_blinds",
            CONF_DRIVE_POSITION: 80,
            CONF_MIN_ANGLE: 10,
            CONF_MAX_ANGLE: 85,
            CONF_INVERT_TILT: True,
            CONF_NO_SUN_BEHAVIOR: "close",
            CONF_NO_SUN_POSITION: 25,
            CONF_RESPECT_MANUAL_CLOSE: False,
            CONF_MANUAL_CLOSE_THRESHOLD: 20,
            CONF_RESPECT_MANUAL_OPEN: False,
            CONF_MANUAL_OPEN_THRESHOLD: 95,
            CONF_MINIMUM_TILT_CHANGE: 10,
            CONF_COVER_ENABLED: False,
            CONF_MIN_TILT_PERCENT: 48,
        }

        config = CoverConfig.from_subentry(subentry)

        assert config.entity_id == "cover.test_blinds"
        assert config.drive_position == 80
        assert config.min_angle == 10
        assert config.max_angle == 85
        assert config.invert_tilt is True
        assert config.no_sun_behavior == "close"
        assert config.no_sun_position == 25
        assert config.respect_manual_close is False
        assert config.manual_close_threshold == 20
        assert config.respect_manual_open is False
        assert config.manual_open_threshold == 95
        assert config.minimum_tilt_change == 10
        assert config.enabled is False
        assert config.min_tilt_percent == 48

    def test_uses_defaults_for_missing(self) -> None:
        """Uses defaults when optional fields are missing."""
        subentry = MagicMock()
        subentry.data = {
            CONF_COVER_ENTITY: "cover.minimal_blinds",
        }

        config = CoverConfig.from_subentry(subentry)

        assert config.entity_id == "cover.minimal_blinds"
        assert config.drive_position == DEFAULT_DRIVE_POSITION
        assert config.min_angle == DEFAULT_MIN_ANGLE
        assert config.max_angle == DEFAULT_MAX_ANGLE
        assert config.invert_tilt == DEFAULT_INVERT_TILT
        assert config.no_sun_behavior == DEFAULT_NO_SUN_BEHAVIOR
        assert config.no_sun_position == DEFAULT_NO_SUN_POSITION
        assert config.respect_manual_close == DEFAULT_RESPECT_MANUAL_CLOSE
        assert config.manual_close_threshold == DEFAULT_MANUAL_CLOSE_THRESHOLD
        assert config.respect_manual_open == DEFAULT_RESPECT_MANUAL_OPEN
        assert config.manual_open_threshold == DEFAULT_MANUAL_OPEN_THRESHOLD
        assert config.minimum_tilt_change == DEFAULT_MINIMUM_TILT_CHANGE
        assert config.enabled == DEFAULT_COVER_ENABLED
        assert config.min_tilt_percent == DEFAULT_MIN_TILT_PERCENT


@pytest.mark.unit
class TestApplyCalculation:
    """Tests for CoverController.apply_calculation via the pipeline."""

    @pytest.fixture
    def mock_controller(self, mock_hass: MagicMock) -> CoverController:
        """Create controller with mocked service calls and state."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100},
        )
        return CoverController(mock_hass)

    @pytest.mark.asyncio
    async def test_skips_disabled_cover(
        self,
        mock_controller: CoverController,
        cover_config_disabled: CoverConfig,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Skips disabled covers."""
        result = await mock_controller.apply_calculation(cover_config_disabled, calculation_result_direct_sun)

        assert result is False
        mock_controller._hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_no_calculation(
        self, mock_controller: CoverController, cover_config_default: CoverConfig
    ) -> None:
        """Handles None calculation (no sun) — keep_last does nothing on first cycle."""
        result = await mock_controller.apply_calculation(cover_config_default, None)
        assert result is False

    @pytest.mark.asyncio
    async def test_handles_sun_behind_facade(
        self,
        mock_controller: CoverController,
        cover_config_default: CoverConfig,
        calculation_result_behind_facade: SlatCalculationResult,
    ) -> None:
        """Handles sun behind facade — keep_last does nothing on first cycle."""
        result = await mock_controller.apply_calculation(cover_config_default, calculation_result_behind_facade)
        assert result is False

    @pytest.mark.asyncio
    async def test_skips_when_position_unavailable(
        self,
        mock_hass: MagicMock,
        cover_config_default: CoverConfig,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Skips when cover state is unavailable."""
        mock_hass.states.get.return_value = None
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        result = await controller.apply_calculation(cover_config_default, calculation_result_direct_sun)

        assert result is False

    @pytest.mark.asyncio
    async def test_respects_manual_close_threshold(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Respects manual close when tilt below threshold."""
        mock_hass.states.get.return_value = create_mock_state(
            state="closed",
            attributes={"current_position": 20, "current_tilt_position": 2},  # Below 5% threshold
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=True,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is False

    @pytest.mark.asyncio
    async def test_clamp_prevents_setting_below_threshold(
        self,
        mock_hass: MagicMock,
    ) -> None:
        """When sun requires 0% tilt, integration clamps to threshold."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 50},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=True,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=False,
        )
        calculation_zero_tilt = SlatCalculationResult(
            slat_angle_deg=0.0,
            slat_tilt_percent=0.0,
            profile_angle_deg=90.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=False,
            sun_elevation_deg=30.0,
        )

        result = await controller.apply_calculation(config, calculation_zero_tilt)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        assert call_args[0][1] == "set_cover_tilt_position"
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 5  # Clamped to threshold

    @pytest.mark.asyncio
    async def test_no_clamp_when_respect_manual_close_disabled(
        self,
        mock_hass: MagicMock,
    ) -> None:
        """When respect_manual_close=False, 0% tilt applies as-is."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 50},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=False,
        )
        calculation_zero_tilt = SlatCalculationResult(
            slat_angle_deg=0.0,
            slat_tilt_percent=0.0,
            profile_angle_deg=90.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=False,
            sun_elevation_deg=30.0,
        )

        result = await controller.apply_calculation(config, calculation_zero_tilt)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 0  # No clamp applied

    @pytest.mark.asyncio
    async def test_ignores_manual_close_when_disabled(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Ignores manual close when respect_manual_close is False."""
        mock_hass.states.get.return_value = create_mock_state(
            state="closed",
            attributes={"current_position": 100, "current_tilt_position": 0},  # Below threshold
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,  # Disabled
            manual_close_threshold=30,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=False,
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is True

    @pytest.mark.asyncio
    async def test_minimum_tilt_change_skips_small_changes(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Skips tilt when change is below minimum threshold."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 48},  # Close to target 50%
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=30,
            minimum_tilt_change=5,  # Require at least 5% change
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=False,
        )

        # calculation_result_direct_sun has slat_tilt_percent=50.0
        # Current tilt is 48%, difference is 2% which is < 5% threshold
        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is False
        mock_hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_applies_tilt_with_inversion(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Applies tilt with inversion."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 0},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=True,  # Invert
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=30,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=False,
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is True
        # calculation_result_direct_sun has slat_tilt_percent=50.0
        # Inverted: 100 - 50 = 50 (stays same at midpoint)
        call_args = mock_hass.services.async_call.call_args
        assert call_args[0][1] == "set_cover_tilt_position"
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 50


@pytest.mark.unit
class TestReflectionProtection:
    """Tests for reflection protection (via NoSunPipe using sun_is_behind_facade)."""

    @pytest.mark.asyncio
    async def test_reflection_protection_disabled_uses_keep_last(self, mock_hass: MagicMock) -> None:
        """With reflection protection disabled and keep_last, nothing is applied."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(state="open", attributes={})
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=30,
            minimum_tilt_change=5,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
        )
        # sun_is_behind_facade=True → NoSunPipe detects no-sun, dispatches keep_last → False
        calculation_behind = SlatCalculationResult(
            slat_angle_deg=0.0,
            slat_tilt_percent=0.0,
            profile_angle_deg=0.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=True,
            sun_elevation_deg=20.0,
        )

        result = await controller.apply_calculation(config, calculation_behind)

        assert result is False
        controller._hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_reflection_protection_active_when_sun_behind_facade(self, mock_hass: MagicMock) -> None:
        """Reflection protection applies min_tilt when sun is behind facade."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(state="open", attributes={})
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=5,
            enabled=True,
            reflection_protection_enabled=True,
            reflection_protection_min_tilt=60,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
        )
        # sun_is_behind_facade=True → reflection protection fires
        calculation_behind = SlatCalculationResult(
            slat_angle_deg=0.0,
            slat_tilt_percent=0.0,
            profile_angle_deg=0.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=True,
            sun_elevation_deg=20.0,
        )

        result = await controller.apply_calculation(config, calculation_behind)

        assert result is True
        call_args = controller._hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 60

    @pytest.mark.asyncio
    async def test_reflection_protection_not_active_when_sun_below_horizon(self, mock_hass: MagicMock) -> None:
        """When sun is below horizon (calculation=None), normal no_sun_behavior is used."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(state="open", attributes={})
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",  # Do nothing
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=5,
            enabled=True,
            reflection_protection_enabled=True,
            reflection_protection_min_tilt=60,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
        )

        # None → below horizon → keep_last → False (not reflection protection)
        result = await controller.apply_calculation(config, None)

        assert result is False
        controller._hass.services.async_call.assert_not_called()


@pytest.mark.unit
class TestMinTiltPercent:
    """Tests for min_tilt_percent floor clamp in apply_calculation."""

    @pytest.mark.asyncio
    async def test_floor_clamps_low_calculated_tilt(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """When calculated tilt is below min_tilt_percent, applies the floor."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 0},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            min_tilt_percent=70,
            respect_manual_open=False,
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 70  # Clamped to floor

    @pytest.mark.asyncio
    async def test_floor_does_not_reduce_higher_tilt(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """When calculated tilt exceeds min_tilt_percent, uses calculated value."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 0},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            min_tilt_percent=30,
            respect_manual_open=False,
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 50  # Calculated value unchanged

    @pytest.mark.asyncio
    async def test_zero_floor_allows_any_tilt(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """When min_tilt_percent=0, floor is inactive."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 0},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            min_tilt_percent=0,
            respect_manual_open=False,
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 50

    @pytest.mark.asyncio
    async def test_floor_applied_after_inversion(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Floor is applied to the post-inversion value."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 0},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        # calculation_result_direct_sun has slat_tilt_percent=50.0
        # After inversion: 100 - 50 = 50. Floor at 60 → clamped to 60.
        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=True,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            min_tilt_percent=60,
            respect_manual_open=False,
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 60  # Floor applied after inversion


@pytest.mark.unit
class TestManualOpenDetection:
    """Tests for manual open / exit-mode detection."""

    @pytest.mark.asyncio
    async def test_skips_when_position_at_threshold(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Skips auto-control when cover position is exactly at the open threshold."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 90, "current_tilt_position": 50},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=50,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=True,
            manual_open_threshold=90,
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is False
        mock_hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_position_above_threshold(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Skips auto-control when cover position is above the open threshold."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 50},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=50,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=True,
            manual_open_threshold=90,
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is False
        mock_hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_applies_when_position_below_threshold(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Applies tilt normally when position is below the open threshold."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 50, "current_tilt_position": 0},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=50,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=True,
            manual_open_threshold=90,
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is True
        mock_hass.services.async_call.assert_called()

    @pytest.mark.asyncio
    async def test_applies_when_feature_disabled(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Applies tilt normally even at high position if respect_manual_open is disabled."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 0},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=False,  # Feature disabled
            manual_open_threshold=90,
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is True
        mock_hass.services.async_call.assert_called()

    @pytest.mark.asyncio
    async def test_bypasses_exit_detection_on_first_sun_hit(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """At sunrise (in_no_sun → sun active), exit detection is bypassed for one cycle.

        This prevents false exit detection when no_sun_behavior='open' raised the cover
        to 100% overnight. The first tracking cycle after the no-sun period should
        drive the cover back down instead of treating 100% as a user-initiated open.
        """
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 100},
        )
        mock_hass.services.async_call = AsyncMock()

        # Pre-set in_no_sun=True — simulates overnight no-sun state.
        # When apply_calculation fires with sun active, NoSunPipe detects the
        # in_no_sun → sun_active transition and sets first_sun_hit=True.
        cover_states = {"cover.test": CoverTrackingState(in_no_sun=True)}
        controller = CoverController(mock_hass, cover_states=cover_states)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=70,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="open",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=True,
            manual_open_threshold=90,  # 100% ≥ threshold, but bypass active
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        # Bypass active → cover should be driven down despite being above threshold
        assert result is True
        mock_hass.services.async_call.assert_called()

    @pytest.mark.asyncio
    async def test_exit_detection_active_after_first_sun_hit(
        self,
        mock_hass: MagicMock,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """After first sun hit, exit detection resumes for subsequent updates."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 95, "current_tilt_position": 50},
        )
        mock_hass.services.async_call = AsyncMock()
        # in_no_sun=False → normal tracking, no bypass
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=70,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=True,
            manual_open_threshold=90,  # 95% ≥ 90% → user raised it
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is False
        mock_hass.services.async_call.assert_not_called()


@pytest.mark.unit
class TestObstacleElevation:
    """Tests for per-cover obstacle elevation angle feature."""

    @pytest.mark.asyncio
    async def test_applies_no_sun_when_sun_below_obstacle(
        self,
        mock_hass: MagicMock,
    ) -> None:
        """When sun elevation <= obstacle angle, no-sun behavior fires instead of tilt."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 0, "current_tilt_position": 50},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=0,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="close",  # Sets tilt to 0% — distinct from normal tilt (50%)
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            obstacle_elevation_deg=20.0,
        )
        # Sun is at 15° — below the 20° obstacle threshold
        calculation = SlatCalculationResult(
            slat_angle_deg=45.0,
            slat_tilt_percent=50.0,
            profile_angle_deg=30.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=False,
            sun_elevation_deg=15.0,
        )

        result = await controller.apply_calculation(config, calculation)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        assert call_args[0][1] == "set_cover_tilt_position"
        assert call_args[0][2]["tilt_position"] == 0

    @pytest.mark.asyncio
    async def test_applies_tilt_when_sun_above_obstacle(
        self,
        mock_hass: MagicMock,
    ) -> None:
        """When sun elevation > obstacle angle, normal tilt is applied."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 50},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="open",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=False,
            obstacle_elevation_deg=10.0,
        )
        # Sun is at 25° — above the 10° obstacle threshold
        calculation = SlatCalculationResult(
            slat_angle_deg=45.0,
            slat_tilt_percent=50.0,
            profile_angle_deg=30.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=False,
            sun_elevation_deg=25.0,
        )

        result = await controller.apply_calculation(config, calculation)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        assert call_args[0][1] == "set_cover_tilt_position"
        assert call_args[0][2]["tilt_position"] == 50

    @pytest.mark.asyncio
    async def test_zero_obstacle_angle_is_disabled(
        self,
        mock_hass: MagicMock,
    ) -> None:
        """obstacle_elevation_deg=0 (default) never triggers no-sun override."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 50},
        )
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="open",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=False,
            obstacle_elevation_deg=0,  # Disabled
        )
        calculation = SlatCalculationResult(
            slat_angle_deg=45.0,
            slat_tilt_percent=50.0,
            profile_angle_deg=30.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=False,
            sun_elevation_deg=1.0,
        )

        result = await controller.apply_calculation(config, calculation)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        assert call_args[0][1] == "set_cover_tilt_position"

    @pytest.mark.asyncio
    async def test_drives_cover_down_when_sun_clears_obstacle(
        self,
        mock_hass: MagicMock,
    ) -> None:
        """Cover is driven back down when sun clears the obstacle threshold.

        Regression: previously the manual-open check (position=100%) blocked this.
        Now the pipeline uses in_no_sun → sun_active transition to set first_sun_hit=True,
        which bypasses exit detection for the first tracking cycle.
        """
        mock_hass.services.async_call = AsyncMock()

        config = CoverConfig(
            entity_id="cover.eg",
            drive_position=0,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="open",
            no_sun_position=100,
            respect_manual_close=False,
            manual_close_threshold=5,
            respect_manual_open=True,
            manual_open_threshold=90,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            obstacle_elevation_deg=10.0,
        )

        # Shared cover_states — persists across controller instances like GroupState
        shared_cover_states: dict[str, CoverTrackingState] = {}

        # Cycle 1: sun at 8° — below obstacle threshold, no-sun fires, in_no_sun set True
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 0, "current_tilt_position": 50},
        )
        below_obstacle = SlatCalculationResult(
            slat_angle_deg=45.0,
            slat_tilt_percent=50.0,
            profile_angle_deg=30.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=False,
            sun_elevation_deg=8.0,
        )
        controller_a = CoverController(mock_hass, cover_states=shared_cover_states)
        await controller_a.apply_calculation(config, below_obstacle)
        assert shared_cover_states.get("cover.eg", CoverTrackingState()).in_no_sun is True

        # Cycle 2: sun at 15° — above obstacle threshold, cover still at 100%
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 100},
        )
        above_obstacle = SlatCalculationResult(
            slat_angle_deg=45.0,
            slat_tilt_percent=50.0,
            profile_angle_deg=30.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=False,
            sun_elevation_deg=15.0,
        )
        controller_b = CoverController(mock_hass, cover_states=shared_cover_states)
        result = await controller_b.apply_calculation(config, above_obstacle)

        # Should drive cover down (bypass exit detection) and apply tilt
        assert result is True
        assert shared_cover_states["cover.eg"].in_no_sun is False
        calls = mock_hass.services.async_call.call_args_list
        service_names = [c[0][1] for c in calls]
        assert "set_cover_position" in service_names


@pytest.mark.unit
class TestAngleBoundsTracking:
    """Tests for max_angle / min_angle enforcement in the tracking path (apply_calculation)."""

    def _make_config(
        self,
        *,
        min_angle: int = 0,
        max_angle: int = 90,
        min_tilt_percent: int = 0,
    ) -> CoverConfig:
        """Return a minimal CoverConfig with the given angle bounds."""
        return CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=min_angle,
            max_angle=max_angle,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=False,
            manual_close_threshold=0,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            min_tilt_percent=min_tilt_percent,
            respect_manual_open=False,
            obstacle_elevation_deg=0,
        )

    def _make_calculation(self, *, slat_tilt_percent: float) -> SlatCalculationResult:
        """Return a calculation with the given tilt."""
        return SlatCalculationResult(
            slat_angle_deg=round(90.0 * (1.0 - slat_tilt_percent / 100.0), 1),
            slat_tilt_percent=slat_tilt_percent,
            profile_angle_deg=20.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=False,
            sun_elevation_deg=10.0,
        )

    @pytest.mark.asyncio
    async def test_max_angle_clamps_overly_closed_tilt(self, mock_hass: MagicMock) -> None:
        """max_angle_deg caps how far the slats can close during tracking."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 100},
        )
        controller = CoverController(mock_hass)

        config = self._make_config(max_angle=45)  # 45° → floor = 50% tilt
        calculation = self._make_calculation(slat_tilt_percent=0.0)

        result = await controller.apply_calculation(config, calculation)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == pytest.approx(50.0)

    @pytest.mark.asyncio
    async def test_max_angle_90_imposes_no_floor(self, mock_hass: MagicMock) -> None:
        """max_angle=90° (default) does not clip any tilt value."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 100},
        )
        controller = CoverController(mock_hass)

        config = self._make_config(max_angle=90)
        calculation = self._make_calculation(slat_tilt_percent=0.0)

        result = await controller.apply_calculation(config, calculation)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 0.0

    @pytest.mark.asyncio
    async def test_max_angle_does_not_reduce_tilt_already_above_floor(self, mock_hass: MagicMock) -> None:
        """max_angle floor is inactive when calculated tilt is already above it."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 0},
        )
        controller = CoverController(mock_hass)

        config = self._make_config(max_angle=45)  # floor = 50%
        calculation = self._make_calculation(slat_tilt_percent=70.0)  # above floor

        result = await controller.apply_calculation(config, calculation)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 70.0

    @pytest.mark.asyncio
    async def test_min_angle_clamps_overly_open_tilt(self, mock_hass: MagicMock) -> None:
        """min_angle_deg caps how far open the slats can be during tracking."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 0},
        )
        controller = CoverController(mock_hass)

        config = self._make_config(min_angle=45)  # 45° → ceiling = 50% tilt
        calculation = self._make_calculation(slat_tilt_percent=90.0)

        result = await controller.apply_calculation(config, calculation)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == pytest.approx(50.0)

    @pytest.mark.asyncio
    async def test_min_angle_0_imposes_no_ceiling(self, mock_hass: MagicMock) -> None:
        """min_angle=0° (default) does not clip any tilt value."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 0},
        )
        controller = CoverController(mock_hass)

        config = self._make_config(min_angle=0)
        calculation = self._make_calculation(slat_tilt_percent=100.0)

        result = await controller.apply_calculation(config, calculation)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 100.0

    @pytest.mark.asyncio
    async def test_angle_bounds_applied_before_inversion(self, mock_hass: MagicMock) -> None:
        """Angle bounds are applied in standard tilt space, before tilt inversion."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 100},
        )
        controller = CoverController(mock_hass)

        config = dataclasses.replace(
            self._make_config(max_angle=45),
            invert_tilt=True,
        )
        calculation = self._make_calculation(slat_tilt_percent=0.0)

        result = await controller.apply_calculation(config, calculation)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        # Standard: 0% clamped to 50% (max_angle floor). Inverted: 100-50 = 50%.
        assert service_data["tilt_position"] == pytest.approx(50.0)


@pytest.mark.unit
class TestAngleBoundsNoSun:
    """Tests for max_angle_deg floor in _effective_min_tilt (no-sun/obstacle path)."""

    def _make_config(
        self,
        *,
        max_angle: int = 90,
        no_sun_behavior: str = "close",
        respect_manual_close: bool = False,
        manual_close_threshold: int = 0,
        min_tilt_percent: int = 0,
    ) -> CoverConfig:
        return CoverConfig(
            entity_id="cover.test",
            drive_position=0,
            min_angle=0,
            max_angle=max_angle,
            invert_tilt=False,
            no_sun_behavior=no_sun_behavior,
            no_sun_position=50,
            respect_manual_close=respect_manual_close,
            manual_close_threshold=manual_close_threshold,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            min_tilt_percent=min_tilt_percent,
            respect_manual_open=False,
            obstacle_elevation_deg=0,
        )

    @pytest.mark.asyncio
    async def test_max_angle_respected_in_no_sun_close(self, mock_hass: MagicMock) -> None:
        """no_sun_behavior='close' respects max_angle_deg via _effective_min_tilt."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 0, "current_tilt_position": 80},
        )
        controller = CoverController(mock_hass)

        config = self._make_config(max_angle=45, no_sun_behavior="close")
        result = await controller.apply_calculation(config, None)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == pytest.approx(50.0)  # 100*(1-45/90)

    @pytest.mark.asyncio
    async def test_max_angle_respected_in_no_sun_set_to_percent(self, mock_hass: MagicMock) -> None:
        """no_sun_behavior='set_to_percent' respects max_angle_deg floor."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 0, "current_tilt_position": 80},
        )
        controller = CoverController(mock_hass)

        config = dataclasses.replace(
            self._make_config(max_angle=45, no_sun_behavior="set_to_percent"),
            no_sun_position=0,
        )
        result = await controller.apply_calculation(config, None)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == pytest.approx(50.0)  # floor wins

    @pytest.mark.asyncio
    async def test_max_angle_90_allows_full_close_in_no_sun(self, mock_hass: MagicMock) -> None:
        """max_angle=90° (default) does not add any floor."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 0, "current_tilt_position": 80},
        )
        controller = CoverController(mock_hass)

        config = self._make_config(max_angle=90, no_sun_behavior="close")
        result = await controller.apply_calculation(config, None)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 0.0

    @pytest.mark.asyncio
    async def test_max_angle_floor_wins_over_manual_close_threshold(self, mock_hass: MagicMock) -> None:
        """When max_angle floor exceeds manual_close_threshold, the floor wins."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 0, "current_tilt_position": 80},
        )
        controller = CoverController(mock_hass)

        # max_angle=45 → floor=50%; manual_close_threshold=10% < 50%, floor wins
        config = self._make_config(
            max_angle=45,
            no_sun_behavior="close",
            respect_manual_close=True,
            manual_close_threshold=10,
        )
        result = await controller.apply_calculation(config, None)

        assert result is True
        call_args = mock_hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == pytest.approx(50.0)


@pytest.mark.unit
class TestCoverStatesPersistence:
    """Tests for cover_states persistence via shared dict (replaces obstacle_was_blocking)."""

    def _make_config(self, *, obstacle_elevation_deg: float = 10.0) -> CoverConfig:
        return CoverConfig(
            entity_id="cover.west",
            drive_position=0,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="open",
            no_sun_position=100,
            respect_manual_close=False,
            manual_close_threshold=5,
            minimum_tilt_change=0,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=True,
            manual_open_threshold=90,
            obstacle_elevation_deg=obstacle_elevation_deg,
        )

    @pytest.mark.asyncio
    async def test_shared_cover_states_persists_across_instances(self, mock_hass: MagicMock) -> None:
        """in_no_sun persists when cover_states dict is shared between controller instances."""
        shared_cover_states: dict[str, CoverTrackingState] = {}
        mock_hass.services.async_call = AsyncMock()
        config = self._make_config(obstacle_elevation_deg=10.0)

        # Cycle 1: sun below obstacle — no-sun fires, in_no_sun=True recorded
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 0, "current_tilt_position": 60},
        )
        controller_a = CoverController(mock_hass, cover_states=shared_cover_states)
        below_obstacle = SlatCalculationResult(
            slat_angle_deg=45.0,
            slat_tilt_percent=50.0,
            profile_angle_deg=30.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=False,
            sun_elevation_deg=8.0,
        )
        await controller_a.apply_calculation(config, below_obstacle)
        assert shared_cover_states.get("cover.west", CoverTrackingState()).in_no_sun is True

        # Cycle 2: NEW controller instance shares the same dict — sun above obstacle
        mock_hass.services.async_call.reset_mock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 100},
        )
        controller_b = CoverController(mock_hass, cover_states=shared_cover_states)
        above_obstacle = SlatCalculationResult(
            slat_angle_deg=45.0,
            slat_tilt_percent=50.0,
            profile_angle_deg=30.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=False,
            sun_elevation_deg=15.0,
        )
        result = await controller_b.apply_calculation(config, above_obstacle)

        # first_sun_hit fires → cover driven back down (bypasses exit detection)
        assert result is True
        assert shared_cover_states["cover.west"].in_no_sun is False
        calls = mock_hass.services.async_call.call_args_list
        service_names = [c[0][1] for c in calls]
        assert "set_cover_position" in service_names

    @pytest.mark.asyncio
    async def test_without_shared_states_transition_bypass_never_fires(self, mock_hass: MagicMock) -> None:
        """Without shared cover_states, in_no_sun transition bypass cannot fire across instances."""
        mock_hass.services.async_call = AsyncMock()
        config = self._make_config(obstacle_elevation_deg=10.0)

        # Cycle 1: below obstacle (separate controller, own private states)
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 0, "current_tilt_position": 60},
        )
        controller_a = CoverController(mock_hass)  # own private cover_states
        below_obstacle = SlatCalculationResult(
            slat_angle_deg=45.0,
            slat_tilt_percent=50.0,
            profile_angle_deg=30.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=False,
            sun_elevation_deg=8.0,
        )
        await controller_a.apply_calculation(config, below_obstacle)

        # Cycle 2: DIFFERENT instance — no shared state, no bypass
        mock_hass.services.async_call.reset_mock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100, "current_tilt_position": 100},
        )
        controller_b = CoverController(mock_hass)  # fresh private cover_states
        above_obstacle = SlatCalculationResult(
            slat_angle_deg=45.0,
            slat_tilt_percent=50.0,
            profile_angle_deg=30.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=False,
            sun_elevation_deg=15.0,
        )
        result = await controller_b.apply_calculation(config, above_obstacle)

        # No bypass → exit detection fires (position=100% ≥ 90%), tracking is skipped
        assert result is False
