"""Tests for CoverController."""

# ruff: noqa: SLF001

from __future__ import annotations

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
class TestGetCoverPosition:
    """Tests for CoverController._get_cover_position method."""

    def test_returns_position_when_present(self, mock_hass: MagicMock) -> None:
        """Returns position when state is present."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 75},
        )

        controller = CoverController(mock_hass)
        result = controller._get_cover_position("cover.test")

        assert result == 75

    def test_returns_none_when_entity_missing(self, mock_hass: MagicMock) -> None:
        """Returns None when entity is missing."""
        mock_hass.states.get.return_value = None

        controller = CoverController(mock_hass)
        result = controller._get_cover_position("cover.test")

        assert result is None

    def test_returns_none_when_attribute_missing(self, mock_hass: MagicMock) -> None:
        """Returns None when position attribute is missing."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={},  # No position attribute
        )

        controller = CoverController(mock_hass)
        result = controller._get_cover_position("cover.test")

        assert result is None

    def test_returns_none_for_invalid_value(self, mock_hass: MagicMock) -> None:
        """Returns None for invalid position value."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": "invalid"},
        )

        controller = CoverController(mock_hass)
        result = controller._get_cover_position("cover.test")

        assert result is None

    def test_converts_float_to_int(self, mock_hass: MagicMock) -> None:
        """Converts float position to int."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 75.5},
        )

        controller = CoverController(mock_hass)
        result = controller._get_cover_position("cover.test")

        assert result == 75


@pytest.mark.unit
class TestHandleNoSun:
    """Tests for CoverController._handle_no_sun method."""

    @pytest.fixture
    def mock_controller(self, mock_hass: MagicMock) -> CoverController:
        """Create controller with mocked service calls."""
        mock_hass.services.async_call = AsyncMock()
        # Return a state with no tilt attribute so _get_cover_tilt returns None,
        # which keeps the manual-close check neutral for tests that don't need it.
        mock_hass.states.get.return_value = create_mock_state(state="open", attributes={})
        return CoverController(mock_hass)

    @pytest.mark.asyncio
    async def test_keep_last_does_nothing(
        self, mock_controller: CoverController, cover_config_default: CoverConfig
    ) -> None:
        """keep_last behavior does nothing."""
        result = await mock_controller._handle_no_sun(cover_config_default)

        assert result is False
        mock_controller._hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_open_raises_position_to_100(
        self, mock_controller: CoverController, cover_config_no_sun_open: CoverConfig
    ) -> None:
        """open behavior raises cover to 100% position (no tilt call needed when fully retracted)."""
        mock_controller._hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 80},
        )
        mock_controller._wait_for_position = AsyncMock(return_value=True)

        result = await mock_controller._handle_no_sun(cover_config_no_sun_open)

        assert result is True
        mock_controller._hass.services.async_call.assert_called_once()
        call_args = mock_controller._hass.services.async_call.call_args
        assert call_args[0][1] == "set_cover_position"
        assert call_args[0][2]["position"] == 100

    @pytest.mark.asyncio
    async def test_open_skips_position_when_already_at_100(
        self, mock_controller: CoverController, cover_config_no_sun_open: CoverConfig
    ) -> None:
        """open behavior does nothing when cover is already at 100%."""
        mock_controller._hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100},
        )

        result = await mock_controller._handle_no_sun(cover_config_no_sun_open)

        assert result is True
        mock_controller._hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_open_skips_position_when_unavailable(
        self, mock_controller: CoverController, cover_config_no_sun_open: CoverConfig
    ) -> None:
        """open behavior does nothing when entity is unavailable."""
        mock_controller._hass.states.get.return_value = None

        result = await mock_controller._handle_no_sun(cover_config_no_sun_open)

        assert result is True
        mock_controller._hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_sets_tilt_0(self, mock_controller: CoverController) -> None:
        """close behavior sets tilt to 0% when respect_manual_close is disabled."""
        config = CoverConfig(
            entity_id="cover.close_blinds",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="close",
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
        result = await mock_controller._handle_no_sun(config)

        assert result is True
        mock_controller._hass.services.async_call.assert_called_once()
        call_args = mock_controller._hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 0

    @pytest.mark.asyncio
    async def test_set_to_percent(
        self,
        mock_controller: CoverController,
        cover_config_no_sun_set_percent: CoverConfig,
    ) -> None:
        """set_to_percent behavior sets to configured percent."""
        result = await mock_controller._handle_no_sun(cover_config_no_sun_set_percent)

        assert result is True
        mock_controller._hass.services.async_call.assert_called_once()
        call_args = mock_controller._hass.services.async_call.call_args
        service_data = call_args[0][2]
        # no_sun_position is 75 in this fixture
        assert service_data["tilt_position"] == 75

    @pytest.mark.asyncio
    async def test_unknown_behavior_returns_false(self, mock_controller: CoverController) -> None:
        """Unknown behavior returns False."""
        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="unknown_behavior",
            no_sun_position=50,
            respect_manual_close=True,
            manual_close_threshold=30,
            minimum_tilt_change=5,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
        )

        result = await mock_controller._handle_no_sun(config)

        assert result is False

    @pytest.mark.asyncio
    async def test_respects_manual_close_when_no_sun(
        self,
        mock_hass: MagicMock,
    ) -> None:
        """no_sun behavior is skipped when slats are manually closed (sleep mode)."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="closed",
            attributes={"current_position": 50, "current_tilt_position": 2},  # Below 5% threshold
        )
        controller = CoverController(mock_hass)

        config = CoverConfig(
            entity_id="cover.west_blinds",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="open",  # Would normally raise the cover
            no_sun_position=50,
            respect_manual_close=True,
            manual_close_threshold=5,
            minimum_tilt_change=5,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
        )

        result = await controller._handle_no_sun(config)

        # Sleep mode should prevent the "open" action
        assert result is False
        mock_hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_sun_proceeds_when_manual_close_not_detected(
        self,
        mock_hass: MagicMock,
    ) -> None:
        """no_sun behavior runs normally when tilt is above manual close threshold."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 80, "current_tilt_position": 50},
        )
        controller = CoverController(mock_hass)
        controller._wait_for_position = AsyncMock(return_value=True)

        config = CoverConfig(
            entity_id="cover.west_blinds",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="open",
            no_sun_position=50,
            respect_manual_close=True,
            manual_close_threshold=5,  # Tilt is 50%, well above threshold
            minimum_tilt_change=5,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
        )

        result = await controller._handle_no_sun(config)

        assert result is True
        mock_hass.services.async_call.assert_called_once()


@pytest.mark.unit
class TestApplyCalculation:
    """Tests for CoverController.apply_calculation method."""

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
        """Handles None calculation (no sun)."""
        # Default behavior is keep_last
        result = await mock_controller.apply_calculation(cover_config_default, None)

        assert result is False

    @pytest.mark.asyncio
    async def test_handles_sun_behind_facade(
        self,
        mock_controller: CoverController,
        cover_config_default: CoverConfig,
        calculation_result_behind_facade: SlatCalculationResult,
    ) -> None:
        """Handles sun behind facade (no direct sun on window)."""
        result = await mock_controller.apply_calculation(cover_config_default, calculation_result_behind_facade)

        # Default behavior is keep_last
        assert result is False

    @pytest.mark.asyncio
    async def test_skips_when_position_unavailable(
        self,
        mock_hass: MagicMock,
        cover_config_default: CoverConfig,
        calculation_result_direct_sun: SlatCalculationResult,
    ) -> None:
        """Skips when cover position is unavailable."""
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
            attributes={"current_position": 20, "current_tilt_position": 2},  # Tilt below 5% threshold
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
            manual_close_threshold=5,  # Threshold is 5% (tilt-based)
            minimum_tilt_change=0,  # No minimum change required
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
        """When sun requires 0% tilt, integration clamps to threshold to preserve manual-close invariant."""
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
        # Sun calculation that would normally yield 0% tilt
        calculation_zero_tilt = SlatCalculationResult(
            slat_angle_deg=0.0,
            slat_tilt_percent=0.0,
            profile_angle_deg=90.0,
            horizontal_shadow_angle_deg=0.0,
            sun_is_behind_facade=False,
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
        """When respect_manual_close=False, 0% tilt applies as-is without clamping."""
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
            attributes={"current_position": 20, "current_tilt_position": 0},  # Below threshold
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
            minimum_tilt_change=0,  # No minimum change required
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        # Should proceed despite being below threshold
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
        # No tilt service should be called
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
            minimum_tilt_change=0,  # No minimum change required
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
            respect_manual_open=False,
        )

        result = await controller.apply_calculation(config, calculation_result_direct_sun)

        assert result is True
        # Check that tilt was called with inverted value
        # calculation_result_direct_sun has slat_tilt_percent=50.0
        # Inverted: 100 - 50 = 50 (stays same at midpoint)
        call_args = mock_hass.services.async_call.call_args
        assert call_args[0][1] == "set_cover_tilt_position"
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 50


@pytest.mark.unit
class TestGetCoverTilt:
    """Tests for CoverController._get_cover_tilt method."""

    def test_returns_tilt_when_present(self, mock_hass: MagicMock) -> None:
        """Returns tilt when attribute is present."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_tilt_position": 45.5},
        )

        controller = CoverController(mock_hass)
        result = controller._get_cover_tilt("cover.test")

        assert result == 45.5

    def test_returns_none_when_entity_missing(self, mock_hass: MagicMock) -> None:
        """Returns None when entity is missing."""
        mock_hass.states.get.return_value = None

        controller = CoverController(mock_hass)
        result = controller._get_cover_tilt("cover.test")

        assert result is None

    def test_returns_none_when_attribute_missing(self, mock_hass: MagicMock) -> None:
        """Returns None when tilt attribute is missing."""
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={},
        )

        controller = CoverController(mock_hass)
        result = controller._get_cover_tilt("cover.test")

        assert result is None


@pytest.mark.unit
class TestReflectionProtection:
    """Tests for reflection protection feature (auto-triggered by sun_has_hit_facade)."""

    def test_disabled_returns_false(self, mock_hass: MagicMock) -> None:
        """Reflection protection disabled returns False regardless of sun state."""
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass, sun_has_hit_facade=True)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=True,
            manual_close_threshold=30,
            minimum_tilt_change=5,
            enabled=True,
            reflection_protection_enabled=False,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
        )

        result = controller._is_reflection_protection_active(config)

        assert result is False

    def test_active_when_sun_has_hit_facade(self, mock_hass: MagicMock) -> None:
        """Returns True when enabled and sun has previously hit the facade."""
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass, sun_has_hit_facade=True)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=True,
            manual_close_threshold=30,
            minimum_tilt_change=5,
            enabled=True,
            reflection_protection_enabled=True,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
        )

        result = controller._is_reflection_protection_active(config)

        assert result is True

    def test_inactive_before_sun_hits_facade(self, mock_hass: MagicMock) -> None:
        """Returns False when sun has not yet hit the facade (e.g., early morning)."""
        mock_hass.services.async_call = AsyncMock()
        controller = CoverController(mock_hass, sun_has_hit_facade=False)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",
            no_sun_position=50,
            respect_manual_close=True,
            manual_close_threshold=30,
            minimum_tilt_change=5,
            enabled=True,
            reflection_protection_enabled=True,
            reflection_protection_min_tilt=50,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
        )

        result = controller._is_reflection_protection_active(config)

        assert result is False

    @pytest.mark.asyncio
    async def test_handle_no_sun_uses_reflection_when_sun_passed(self, mock_hass: MagicMock) -> None:
        """When sun has passed facade, reflection protection sets min tilt instead of no_sun_behavior."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(state="open", attributes={})
        controller = CoverController(mock_hass, sun_has_hit_facade=True)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="keep_last",  # Would normally do nothing
            no_sun_position=50,
            respect_manual_close=True,
            manual_close_threshold=30,
            minimum_tilt_change=5,
            enabled=True,
            reflection_protection_enabled=True,
            reflection_protection_min_tilt=60,  # Should use this value
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
        )

        result = await controller._handle_no_sun(config)

        assert result is True
        controller._hass.services.async_call.assert_called_once()
        call_args = controller._hass.services.async_call.call_args
        service_data = call_args[0][2]
        assert service_data["tilt_position"] == 60

    @pytest.mark.asyncio
    async def test_handle_no_sun_falls_back_when_sun_not_hit(self, mock_hass: MagicMock) -> None:
        """When sun hasn't hit facade yet, uses normal no_sun_behavior."""
        mock_hass.services.async_call = AsyncMock()
        mock_hass.states.get.return_value = create_mock_state(
            state="open",
            attributes={"current_position": 100},  # Already at 100%, position call skipped
        )
        controller = CoverController(mock_hass, sun_has_hit_facade=False)

        config = CoverConfig(
            entity_id="cover.test",
            drive_position=100,
            min_angle=0,
            max_angle=90,
            invert_tilt=False,
            no_sun_behavior="open",  # Should use this
            no_sun_position=50,
            respect_manual_close=True,
            manual_close_threshold=30,
            minimum_tilt_change=5,
            enabled=True,
            reflection_protection_enabled=True,
            reflection_protection_min_tilt=60,
            reflection_protection_start_time="09:00",
            reflection_protection_end_time="17:00",
        )

        result = await controller._handle_no_sun(config)

        assert result is True
        # Position already at 100%, no service call needed
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

        # calculation_result_direct_sun has slat_tilt_percent=50.0
        # Set floor at 70% so calculated value (50%) gets clamped
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

        # calculation_result_direct_sun has slat_tilt_percent=50.0
        # Set floor at 30% — calculated value (50%) is already above it
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
        """When min_tilt_percent=0, floor is inactive and low tilt values pass through."""
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
        assert service_data["tilt_position"] == 50  # calculation_result_direct_sun value

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
    """Tests for manual open detection (patio door / exit mode)."""

    @pytest.fixture
    def mock_controller(self, mock_hass: MagicMock) -> CoverController:
        """Create controller with mocked service calls."""
        mock_hass.services.async_call = AsyncMock()
        return CoverController(mock_hass)

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
        """Skips auto-control when cover position is above the open threshold (e.g. 100%)."""
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
        """Applies tilt normally even when position is above threshold if feature is disabled."""
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

        # Despite position being 100% (above threshold), should proceed because feature is off
        assert result is True
        mock_hass.services.async_call.assert_called()
