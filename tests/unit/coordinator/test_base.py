"""Tests for SmartVenetianBlindsDataUpdateCoordinator._calculate_slat_angle state management."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.smart_venetian_blinds.coordinator.base import SmartVenetianBlindsDataUpdateCoordinator
from custom_components.smart_venetian_blinds.coordinator.state import GroupState
from custom_components.smart_venetian_blinds.sun.math import SunPosition


def _make_coordinator(*, sun_position: SunPosition | None) -> SmartVenetianBlindsDataUpdateCoordinator:
    """Build a coordinator wired to a sun provider that returns *sun_position*."""
    hass = MagicMock()
    hass.loop = MagicMock()

    sun_provider = MagicMock()
    sun_provider.get_sun_position.return_value = sun_position

    config_entry = MagicMock()
    config_entry.data = {
        "facade_azimuth": 180,
        "slat_width": 80,
        "slat_spacing": 70,
        "safety_margin": 0,
    }
    config_entry.runtime_data.state = GroupState()

    coordinator = SmartVenetianBlindsDataUpdateCoordinator.__new__(SmartVenetianBlindsDataUpdateCoordinator)
    coordinator._hass = hass
    coordinator._sun_provider = sun_provider
    coordinator.config_entry = config_entry
    coordinator.logger = MagicMock()
    return coordinator


# Sun positions for tests
_SUN_BELOW_HORIZON = SunPosition(azimuth_deg=180.0, elevation_deg=-5.0)
_SUN_ON_SOUTH_FACADE = SunPosition(azimuth_deg=180.0, elevation_deg=45.0)
_SUN_BEHIND_SOUTH_FACADE = SunPosition(azimuth_deg=0.0, elevation_deg=20.0)


@pytest.mark.unit
class TestNoSunActionAppliedReset:
    """Regression tests for the no_sun_action_applied flag reset bug.

    The sun entity keeps firing state-change events even after sunset (azimuth/elevation
    still change). no_sun_action_applied must NOT be reset on every below-horizon update —
    only when the sun re-appears on the facade (start of new solar day).
    """

    def test_no_sun_action_applied_not_reset_when_sun_below_horizon(self) -> None:
        """no_sun_action_applied stays True while sun remains below the horizon."""
        coordinator = _make_coordinator(sun_position=_SUN_BELOW_HORIZON)
        state = coordinator.config_entry.runtime_data.state

        # Simulate: no-sun action was already applied this period
        state.no_sun_action_applied = True
        state.sun_has_hit_facade = False

        result = coordinator._calculate_slat_angle()

        assert result is None
        assert state.no_sun_action_applied is True, (
            "no_sun_action_applied must NOT be reset when sun is below the horizon"
        )

    def test_sun_has_hit_facade_reset_when_sun_below_horizon(self) -> None:
        """sun_has_hit_facade IS reset when sun goes below horizon (correct behaviour)."""
        coordinator = _make_coordinator(sun_position=_SUN_BELOW_HORIZON)
        state = coordinator.config_entry.runtime_data.state
        state.sun_has_hit_facade = True

        coordinator._calculate_slat_angle()

        assert state.sun_has_hit_facade is False

    def test_no_sun_action_applied_reset_when_sun_hits_facade(self) -> None:
        """no_sun_action_applied IS reset when the sun comes back on the facade (new solar day)."""
        coordinator = _make_coordinator(sun_position=_SUN_ON_SOUTH_FACADE)
        state = coordinator.config_entry.runtime_data.state

        state.no_sun_action_applied = True
        state.sun_has_hit_facade = False

        result = coordinator._calculate_slat_angle()

        assert result is not None
        assert result.sun_is_behind_facade is False
        assert state.no_sun_action_applied is False, (
            "no_sun_action_applied must reset when the sun returns to the facade"
        )
        assert state.sun_has_hit_facade is True

    def test_no_sun_action_applied_preserved_when_sun_behind_facade(self) -> None:
        """no_sun_action_applied is unchanged when sun is above horizon but behind facade."""
        coordinator = _make_coordinator(sun_position=_SUN_BEHIND_SOUTH_FACADE)
        state = coordinator.config_entry.runtime_data.state

        state.no_sun_action_applied = True

        result = coordinator._calculate_slat_angle()

        assert result is not None
        assert result.sun_is_behind_facade is True
        # Flag must be left unchanged (not reset, not set)
        assert state.no_sun_action_applied is True
