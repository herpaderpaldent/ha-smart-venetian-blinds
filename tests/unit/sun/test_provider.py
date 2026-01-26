"""Tests for SunDataProvider."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.smart_venetian_blinds.const import SENSOR_SUN_AZIMUTH, SENSOR_SUN_ELEVATION, SUN_ENTITY
from custom_components.smart_venetian_blinds.sun.provider import SunDataProvider
from tests.conftest import create_mock_state


@pytest.mark.unit
class TestGetFromSensors:
    """Tests for SunDataProvider._get_from_sensors method."""

    def test_both_sensors_present(self, mock_hass: MagicMock) -> None:
        """Returns SunPosition when both sensors are present."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SENSOR_SUN_AZIMUTH: create_mock_state(state="135.5"),
            SENSOR_SUN_ELEVATION: create_mock_state(state="45.2"),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider._get_from_sensors()

        assert result is not None
        assert result.azimuth_deg == 135.5
        assert result.elevation_deg == 45.2

    def test_azimuth_sensor_missing(self, mock_hass: MagicMock) -> None:
        """Returns None when azimuth sensor is missing."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SENSOR_SUN_ELEVATION: create_mock_state(state="45.2"),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider._get_from_sensors()

        assert result is None

    def test_elevation_sensor_missing(self, mock_hass: MagicMock) -> None:
        """Returns None when elevation sensor is missing."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SENSOR_SUN_AZIMUTH: create_mock_state(state="135.5"),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider._get_from_sensors()

        assert result is None

    def test_both_sensors_missing(self, mock_hass: MagicMock) -> None:
        """Returns None when both sensors are missing."""
        mock_hass.states.get.return_value = None

        provider = SunDataProvider(mock_hass)
        result = provider._get_from_sensors()

        assert result is None

    def test_invalid_azimuth_value(self, mock_hass: MagicMock) -> None:
        """Returns None when azimuth has invalid value."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SENSOR_SUN_AZIMUTH: create_mock_state(state="unavailable"),
            SENSOR_SUN_ELEVATION: create_mock_state(state="45.2"),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider._get_from_sensors()

        assert result is None

    def test_invalid_elevation_value(self, mock_hass: MagicMock) -> None:
        """Returns None when elevation has invalid value."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SENSOR_SUN_AZIMUTH: create_mock_state(state="135.5"),
            SENSOR_SUN_ELEVATION: create_mock_state(state="unknown"),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider._get_from_sensors()

        assert result is None

    def test_integer_values(self, mock_hass: MagicMock) -> None:
        """Handles integer values correctly."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SENSOR_SUN_AZIMUTH: create_mock_state(state="180"),
            SENSOR_SUN_ELEVATION: create_mock_state(state="60"),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider._get_from_sensors()

        assert result is not None
        assert result.azimuth_deg == 180.0
        assert result.elevation_deg == 60.0

    def test_negative_elevation(self, mock_hass: MagicMock) -> None:
        """Handles negative elevation values."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SENSOR_SUN_AZIMUTH: create_mock_state(state="180.0"),
            SENSOR_SUN_ELEVATION: create_mock_state(state="-5.5"),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider._get_from_sensors()

        assert result is not None
        assert result.elevation_deg == -5.5


@pytest.mark.unit
class TestGetFromSunEntity:
    """Tests for SunDataProvider._get_from_sun_entity method."""

    def test_sun_entity_present(self, mock_hass: MagicMock) -> None:
        """Returns SunPosition when sun.sun entity is present."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SUN_ENTITY: create_mock_state(
                state="above_horizon",
                attributes={"azimuth": 180.5, "elevation": 45.2},
            ),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider._get_from_sun_entity()

        assert result is not None
        assert result.azimuth_deg == 180.5
        assert result.elevation_deg == 45.2

    def test_sun_entity_missing(self, mock_hass: MagicMock) -> None:
        """Returns None when sun.sun entity is missing."""
        mock_hass.states.get.return_value = None

        provider = SunDataProvider(mock_hass)
        result = provider._get_from_sun_entity()

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
        result = provider._get_from_sun_entity()

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
        result = provider._get_from_sun_entity()

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
        result = provider._get_from_sun_entity()

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
        result = provider._get_from_sun_entity()

        # float(None) raises TypeError, which is caught and returns None
        assert result is None


@pytest.mark.unit
class TestGetSunPosition:
    """Tests for SunDataProvider.get_sun_position method."""

    def test_prefers_sensors_over_sun_entity(self, mock_hass: MagicMock) -> None:
        """Prefers sensors over sun.sun entity."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SENSOR_SUN_AZIMUTH: create_mock_state(state="100.0"),
            SENSOR_SUN_ELEVATION: create_mock_state(state="30.0"),
            SUN_ENTITY: create_mock_state(
                state="above_horizon",
                attributes={"azimuth": 200.0, "elevation": 50.0},
            ),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider.get_sun_position()

        assert result is not None
        # Should get values from sensors, not sun.sun
        assert result.azimuth_deg == 100.0
        assert result.elevation_deg == 30.0

    def test_falls_back_to_sun_entity(self, mock_hass: MagicMock) -> None:
        """Falls back to sun.sun when sensors are missing."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            # No sensor entities
            SUN_ENTITY: create_mock_state(
                state="above_horizon",
                attributes={"azimuth": 200.0, "elevation": 50.0},
            ),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider.get_sun_position()

        assert result is not None
        assert result.azimuth_deg == 200.0
        assert result.elevation_deg == 50.0

    def test_returns_none_when_all_missing(self, mock_hass: MagicMock) -> None:
        """Returns None when all sources are missing."""
        mock_hass.states.get.return_value = None

        provider = SunDataProvider(mock_hass)
        result = provider.get_sun_position()

        assert result is None


@pytest.mark.unit
class TestGetTrackedEntities:
    """Tests for SunDataProvider.get_tracked_entities method."""

    def test_returns_sensors_when_both_present(self, mock_hass: MagicMock) -> None:
        """Returns sensor entity IDs when both are present."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SENSOR_SUN_AZIMUTH: create_mock_state(state="100.0"),
            SENSOR_SUN_ELEVATION: create_mock_state(state="30.0"),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider.get_tracked_entities()

        assert result == [SENSOR_SUN_AZIMUTH, SENSOR_SUN_ELEVATION]

    def test_returns_sun_entity_when_sensors_missing(self, mock_hass: MagicMock) -> None:
        """Returns sun.sun when sensors are missing."""
        mock_hass.states.get.return_value = None

        provider = SunDataProvider(mock_hass)
        result = provider.get_tracked_entities()

        assert result == [SUN_ENTITY]

    def test_returns_sun_entity_when_only_azimuth_present(self, mock_hass: MagicMock) -> None:
        """Returns sun.sun when only azimuth sensor present."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SENSOR_SUN_AZIMUTH: create_mock_state(state="100.0"),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider.get_tracked_entities()

        assert result == [SUN_ENTITY]

    def test_returns_sun_entity_when_only_elevation_present(self, mock_hass: MagicMock) -> None:
        """Returns sun.sun when only elevation sensor present."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SENSOR_SUN_ELEVATION: create_mock_state(state="30.0"),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        result = provider.get_tracked_entities()

        assert result == [SUN_ENTITY]


@pytest.mark.unit
class TestIsAvailable:
    """Tests for SunDataProvider.is_available property."""

    def test_available_with_sensors(self, mock_hass: MagicMock) -> None:
        """Returns True when sensors are available."""
        mock_hass.states.get.side_effect = lambda entity_id: {
            SENSOR_SUN_AZIMUTH: create_mock_state(state="100.0"),
            SENSOR_SUN_ELEVATION: create_mock_state(state="30.0"),
        }.get(entity_id)

        provider = SunDataProvider(mock_hass)
        assert provider.is_available is True

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

    def test_not_available_when_all_missing(self, mock_hass: MagicMock) -> None:
        """Returns False when all sources are missing."""
        mock_hass.states.get.return_value = None

        provider = SunDataProvider(mock_hass)
        assert provider.is_available is False
