"""Tests for SunDataProvider."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.smart_venetian_blinds.const import SUN_ENTITY
from custom_components.smart_venetian_blinds.sun.provider import SunDataProvider
from tests.conftest import create_mock_state


@pytest.mark.unit
class TestGetSunPosition:
    """Tests for SunDataProvider.get_sun_position method."""

    def test_sun_entity_present(self, mock_hass: MagicMock) -> None:
        """Returns SunPosition when sun.sun entity is present."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SUN_ENTITY: create_mock_state(
                state="above_horizon",
                attributes={"azimuth": 180.5, "elevation": 45.2},
            ),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider.get_sun_position()

        assert result is not None
        assert result.azimuth_deg == 180.5
        assert result.elevation_deg == 45.2

    def test_sun_entity_missing(self, mock_hass: MagicMock) -> None:
        """Returns None when sun.sun entity is missing."""
        mock_hass.states.get.return_value = None

        provider = SunDataProvider(mock_hass)
        result = provider.get_sun_position()

        assert result is None

    def test_missing_azimuth_attribute_defaults_to_zero(self, mock_hass: MagicMock) -> None:
        """Missing azimuth attribute defaults to 0."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SUN_ENTITY: create_mock_state(
                state="above_horizon",
                attributes={"elevation": 45.2},  # No azimuth
            ),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider.get_sun_position()

        assert result is not None
        assert result.azimuth_deg == 0.0
        assert result.elevation_deg == 45.2

    def test_missing_elevation_attribute_defaults_to_zero(self, mock_hass: MagicMock) -> None:
        """Missing elevation attribute defaults to 0."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SUN_ENTITY: create_mock_state(
                state="above_horizon",
                attributes={"azimuth": 180.5},  # No elevation
            ),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider.get_sun_position()

        assert result is not None
        assert result.azimuth_deg == 180.5
        assert result.elevation_deg == 0.0

    def test_invalid_attribute_values(self, mock_hass: MagicMock) -> None:
        """Returns None when attributes have invalid values."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SUN_ENTITY: create_mock_state(
                state="above_horizon",
                attributes={"azimuth": "invalid", "elevation": "bad"},
            ),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider.get_sun_position()

        assert result is None

    def test_none_attribute_values_returns_none(self, mock_hass: MagicMock) -> None:
        """Returns None when attributes have None values (float(None) fails)."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SUN_ENTITY: create_mock_state(
                state="above_horizon",
                attributes={"azimuth": None, "elevation": None},
            ),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider.get_sun_position()

        # float(None) raises TypeError, which is caught and returns None
        assert result is None


@pytest.mark.unit
class TestGetTrackedEntities:
    """Tests for SunDataProvider.get_tracked_entities method."""

    def test_returns_sun_entity(self, mock_hass: MagicMock) -> None:
        """Returns sun.sun entity ID."""
        provider = SunDataProvider(mock_hass)
        result = provider.get_tracked_entities()

        assert result == [SUN_ENTITY]


@pytest.mark.unit
class TestIsAvailable:
    """Tests for SunDataProvider.is_available property."""

    def test_available_with_sun_entity(self, mock_hass: MagicMock) -> None:
        """Returns True when sun.sun is available."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SUN_ENTITY: create_mock_state(
                state="above_horizon",
                attributes={"azimuth": 200.0, "elevation": 50.0},
            ),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        assert provider.is_available is True

    def test_not_available_when_missing(self, mock_hass: MagicMock) -> None:
        """Returns False when sun.sun is missing."""
        mock_hass.states.get.return_value = None

        provider = SunDataProvider(mock_hass)
        assert provider.is_available is False
