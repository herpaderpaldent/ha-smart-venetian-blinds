"""Shared fixtures for Smart Venetian Blinds tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from custom_components.smart_venetian_blinds.cover_control.controller import CoverConfig
from custom_components.smart_venetian_blinds.sun.math import SlatCalculationResult, SunPosition

if TYPE_CHECKING:
    from collections.abc import Generator


# === Sun Position Fixtures ===


@pytest.fixture
def sun_position_midday() -> SunPosition:
    """Sun at midday, high elevation, south-facing."""
    return SunPosition(azimuth_deg=180.0, elevation_deg=60.0)


@pytest.fixture
def sun_position_morning() -> SunPosition:
    """Sun in the morning, low elevation, east-facing."""
    return SunPosition(azimuth_deg=90.0, elevation_deg=30.0)


@pytest.fixture
def sun_position_evening() -> SunPosition:
    """Sun in the evening, low elevation, west-facing."""
    return SunPosition(azimuth_deg=270.0, elevation_deg=20.0)


@pytest.fixture
def sun_position_below_horizon() -> SunPosition:
    """Sun below the horizon."""
    return SunPosition(azimuth_deg=180.0, elevation_deg=-5.0)


@pytest.fixture
def sun_position_at_horizon() -> SunPosition:
    """Sun exactly at the horizon."""
    return SunPosition(azimuth_deg=180.0, elevation_deg=0.0)


# === Calculation Result Fixtures ===


@pytest.fixture
def calculation_result_direct_sun() -> SlatCalculationResult:
    """Calculation result for direct sunlight."""
    return SlatCalculationResult(
        slat_angle_deg=45.0,
        slat_tilt_percent=50.0,
        profile_angle_deg=60.0,
        horizontal_shadow_angle_deg=0.0,
        sun_is_behind_facade=False,
    )


@pytest.fixture
def calculation_result_behind_facade() -> SlatCalculationResult:
    """Calculation result when sun is behind facade."""
    return SlatCalculationResult(
        slat_angle_deg=0.0,
        slat_tilt_percent=100.0,
        profile_angle_deg=0.0,
        horizontal_shadow_angle_deg=120.0,
        sun_is_behind_facade=True,
    )


# === Cover Config Fixtures ===


@pytest.fixture
def cover_config_default() -> CoverConfig:
    """Default cover configuration."""
    return CoverConfig(
        entity_id="cover.living_room_blinds",
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


@pytest.fixture
def cover_config_inverted() -> CoverConfig:
    """Cover configuration with inverted tilt."""
    return CoverConfig(
        entity_id="cover.bedroom_blinds",
        drive_position=100,
        min_angle=0,
        max_angle=90,
        invert_tilt=True,
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


@pytest.fixture
def cover_config_disabled() -> CoverConfig:
    """Disabled cover configuration."""
    return CoverConfig(
        entity_id="cover.disabled_blinds",
        drive_position=100,
        min_angle=0,
        max_angle=90,
        invert_tilt=False,
        no_sun_behavior="keep_last",
        no_sun_position=50,
        respect_manual_close=True,
        manual_close_threshold=30,
        minimum_tilt_change=5,
        enabled=False,
        reflection_protection_enabled=False,
        reflection_protection_min_tilt=50,
        reflection_protection_start_time="09:00",
        reflection_protection_end_time="17:00",
    )


@pytest.fixture
def cover_config_no_sun_open() -> CoverConfig:
    """Cover configuration with no_sun_behavior='open'."""
    return CoverConfig(
        entity_id="cover.open_blinds",
        drive_position=100,
        min_angle=0,
        max_angle=90,
        invert_tilt=False,
        no_sun_behavior="open",
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


@pytest.fixture
def cover_config_no_sun_close() -> CoverConfig:
    """Cover configuration with no_sun_behavior='close'."""
    return CoverConfig(
        entity_id="cover.close_blinds",
        drive_position=100,
        min_angle=0,
        max_angle=90,
        invert_tilt=False,
        no_sun_behavior="close",
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


@pytest.fixture
def cover_config_no_sun_set_percent() -> CoverConfig:
    """Cover configuration with no_sun_behavior='set_to_percent'."""
    return CoverConfig(
        entity_id="cover.percent_blinds",
        drive_position=100,
        min_angle=0,
        max_angle=90,
        invert_tilt=False,
        no_sun_behavior="set_to_percent",
        no_sun_position=75,
        respect_manual_close=True,
        manual_close_threshold=30,
        minimum_tilt_change=5,
        enabled=True,
        reflection_protection_enabled=False,
        reflection_protection_min_tilt=50,
        reflection_protection_start_time="09:00",
        reflection_protection_end_time="17:00",
    )


# === Mock Home Assistant Fixtures ===


@pytest.fixture
def mock_hass() -> Generator[MagicMock]:
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = MagicMock()
    return hass


def create_mock_state(
    state: str = "open",
    attributes: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock state object."""
    mock_state = MagicMock()
    mock_state.state = state
    mock_state.attributes = attributes or {}
    return mock_state
