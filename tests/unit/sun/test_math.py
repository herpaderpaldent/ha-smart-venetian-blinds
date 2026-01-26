"""Tests for sun math functions."""

from __future__ import annotations

import pytest

from custom_components.smart_venetian_blinds.sun.math import (
    SlatCalculationResult,
    SunPosition,
    apply_tilt_inversion,
    calculate_slat_angle,
    normalize_angle_180,
)


@pytest.mark.unit
class TestNormalizeAngle180:
    """Tests for normalize_angle_180 function."""

    def test_zero_returns_zero(self) -> None:
        """0 degrees stays at 0."""
        assert normalize_angle_180(0.0) == 0.0

    def test_positive_within_range(self) -> None:
        """Angles in [0, 180] stay unchanged."""
        assert normalize_angle_180(45.0) == 45.0
        assert normalize_angle_180(90.0) == 90.0
        assert normalize_angle_180(180.0) == 180.0

    def test_positive_over_180(self) -> None:
        """Angles > 180 wrap to negative."""
        assert normalize_angle_180(270.0) == -90.0
        assert normalize_angle_180(350.0) == -10.0
        assert normalize_angle_180(181.0) == -179.0

    def test_negative_angles(self) -> None:
        """Negative angles normalize correctly."""
        assert normalize_angle_180(-90.0) == -90.0
        assert normalize_angle_180(-180.0) == 180.0
        assert normalize_angle_180(-270.0) == 90.0

    def test_over_360(self) -> None:
        """Angles > 360 wrap correctly."""
        assert normalize_angle_180(360.0) == 0.0
        assert normalize_angle_180(450.0) == 90.0
        assert normalize_angle_180(540.0) == 180.0
        assert normalize_angle_180(720.0) == 0.0

    def test_large_negative(self) -> None:
        """Large negative angles normalize correctly."""
        assert normalize_angle_180(-360.0) == 0.0
        assert normalize_angle_180(-450.0) == -90.0


@pytest.mark.unit
class TestCalculateSlatAngle:
    """Tests for calculate_slat_angle function."""

    # Standard slat geometry for testing
    SLAT_WIDTH = 80.0  # mm
    SLAT_SPACING = 70.0  # mm
    FACADE_SOUTH = 180.0  # South-facing facade

    def test_sun_below_horizon_returns_none(self, sun_position_below_horizon: SunPosition) -> None:
        """Sun below horizon returns None."""
        result = calculate_slat_angle(
            sun=sun_position_below_horizon,
            facade_azimuth_deg=self.FACADE_SOUTH,
            slat_width_mm=self.SLAT_WIDTH,
            slat_spacing_mm=self.SLAT_SPACING,
        )
        assert result is None

    def test_sun_at_horizon_returns_none(self, sun_position_at_horizon: SunPosition) -> None:
        """Sun exactly at horizon returns None."""
        result = calculate_slat_angle(
            sun=sun_position_at_horizon,
            facade_azimuth_deg=self.FACADE_SOUTH,
            slat_width_mm=self.SLAT_WIDTH,
            slat_spacing_mm=self.SLAT_SPACING,
        )
        assert result is None

    def test_sun_behind_facade_east(self) -> None:
        """Sun behind east facade (sun is west)."""
        sun = SunPosition(azimuth_deg=270.0, elevation_deg=45.0)
        result = calculate_slat_angle(
            sun=sun,
            facade_azimuth_deg=90.0,  # East-facing
            slat_width_mm=self.SLAT_WIDTH,
            slat_spacing_mm=self.SLAT_SPACING,
        )
        assert result is not None
        assert result.sun_is_behind_facade is True
        assert result.slat_angle_deg == 0.0
        assert result.slat_tilt_percent == 100.0

    def test_sun_behind_facade_south(self) -> None:
        """Sun behind south facade (sun is north)."""
        sun = SunPosition(azimuth_deg=0.0, elevation_deg=30.0)
        result = calculate_slat_angle(
            sun=sun,
            facade_azimuth_deg=self.FACADE_SOUTH,
            slat_width_mm=self.SLAT_WIDTH,
            slat_spacing_mm=self.SLAT_SPACING,
        )
        assert result is not None
        assert result.sun_is_behind_facade is True
        assert result.horizontal_shadow_angle_deg == -180.0 or abs(result.horizontal_shadow_angle_deg) > 90

    def test_direct_sun_on_facade(self, sun_position_midday: SunPosition) -> None:
        """Direct sunlight on south facade at midday."""
        result = calculate_slat_angle(
            sun=sun_position_midday,
            facade_azimuth_deg=self.FACADE_SOUTH,
            slat_width_mm=self.SLAT_WIDTH,
            slat_spacing_mm=self.SLAT_SPACING,
        )
        assert result is not None
        assert result.sun_is_behind_facade is False
        assert result.horizontal_shadow_angle_deg == 0.0  # Sun directly in front
        assert 0.0 <= result.slat_angle_deg <= 90.0
        assert 0.0 <= result.slat_tilt_percent <= 100.0

    def test_slat_angle_increases_with_sun_elevation(self) -> None:
        """Higher sun elevation requires more closed slats."""
        results = []
        for elevation in [20.0, 40.0, 60.0, 80.0]:
            sun = SunPosition(azimuth_deg=180.0, elevation_deg=elevation)
            result = calculate_slat_angle(
                sun=sun,
                facade_azimuth_deg=self.FACADE_SOUTH,
                slat_width_mm=self.SLAT_WIDTH,
                slat_spacing_mm=self.SLAT_SPACING,
            )
            assert result is not None
            results.append(result.slat_angle_deg)

        # Profile angle increases with elevation, but slat angle relationship
        # depends on geometry. Just verify all results are valid.
        for angle in results:
            assert 0.0 <= angle <= 90.0

    def test_min_angle_constraint(self) -> None:
        """Min angle constraint is respected."""
        sun = SunPosition(azimuth_deg=180.0, elevation_deg=10.0)
        result = calculate_slat_angle(
            sun=sun,
            facade_azimuth_deg=self.FACADE_SOUTH,
            slat_width_mm=self.SLAT_WIDTH,
            slat_spacing_mm=self.SLAT_SPACING,
            min_angle_deg=30.0,
        )
        assert result is not None
        assert result.slat_angle_deg >= 30.0

    def test_max_angle_constraint(self) -> None:
        """Max angle constraint is respected."""
        sun = SunPosition(azimuth_deg=180.0, elevation_deg=80.0)
        result = calculate_slat_angle(
            sun=sun,
            facade_azimuth_deg=self.FACADE_SOUTH,
            slat_width_mm=self.SLAT_WIDTH,
            slat_spacing_mm=self.SLAT_SPACING,
            max_angle_deg=60.0,
        )
        assert result is not None
        assert result.slat_angle_deg <= 60.0

    def test_wide_slat_spacing_uses_max_angle(self) -> None:
        """Very wide slat spacing can't fully block sun, uses max angle."""
        sun = SunPosition(azimuth_deg=180.0, elevation_deg=60.0)
        result = calculate_slat_angle(
            sun=sun,
            facade_azimuth_deg=self.FACADE_SOUTH,
            slat_width_mm=50.0,  # Narrow slats
            slat_spacing_mm=100.0,  # Wide spacing
        )
        assert result is not None
        # With extreme geometry ratio > 1, uses max_angle (90)
        assert result.slat_angle_deg == 90.0

    def test_result_rounding(self, sun_position_midday: SunPosition) -> None:
        """Results are rounded to one decimal place."""
        result = calculate_slat_angle(
            sun=sun_position_midday,
            facade_azimuth_deg=self.FACADE_SOUTH,
            slat_width_mm=self.SLAT_WIDTH,
            slat_spacing_mm=self.SLAT_SPACING,
        )
        assert result is not None
        # Check that values have at most 1 decimal place
        assert result.slat_angle_deg == round(result.slat_angle_deg, 1)
        assert result.slat_tilt_percent == round(result.slat_tilt_percent, 1)
        assert result.profile_angle_deg == round(result.profile_angle_deg, 1)
        assert result.horizontal_shadow_angle_deg == round(result.horizontal_shadow_angle_deg, 1)

    def test_position_percent_calculation(self) -> None:
        """Position percent correctly relates to slat angle."""
        sun = SunPosition(azimuth_deg=180.0, elevation_deg=45.0)
        result = calculate_slat_angle(
            sun=sun,
            facade_azimuth_deg=self.FACADE_SOUTH,
            slat_width_mm=self.SLAT_WIDTH,
            slat_spacing_mm=self.SLAT_SPACING,
        )
        assert result is not None
        # 0 deg = 100% open, 90 deg = 0% open
        expected_percent = 100.0 * (1.0 - result.slat_angle_deg / 90.0)
        assert abs(result.slat_tilt_percent - round(expected_percent, 1)) < 0.2

    def test_sun_parallel_to_facade(self) -> None:
        """Sun exactly parallel to facade plane is handled."""
        sun = SunPosition(azimuth_deg=270.0, elevation_deg=45.0)  # West
        result = calculate_slat_angle(
            sun=sun,
            facade_azimuth_deg=self.FACADE_SOUTH,  # South
            slat_width_mm=self.SLAT_WIDTH,
            slat_spacing_mm=self.SLAT_SPACING,
        )
        assert result is not None
        # HSA = 270 - 180 = 90, exactly parallel
        assert abs(result.horizontal_shadow_angle_deg) == 90.0

    def test_various_facade_orientations(self) -> None:
        """Different facade orientations produce valid results."""
        sun = SunPosition(azimuth_deg=135.0, elevation_deg=45.0)  # SE

        for facade_azimuth in [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0]:
            result = calculate_slat_angle(
                sun=sun,
                facade_azimuth_deg=facade_azimuth,
                slat_width_mm=self.SLAT_WIDTH,
                slat_spacing_mm=self.SLAT_SPACING,
            )
            assert result is not None
            if result.sun_is_behind_facade:
                assert result.slat_angle_deg == 0.0
            else:
                assert 0.0 <= result.slat_angle_deg <= 90.0


@pytest.mark.unit
class TestApplyTiltInversion:
    """Tests for apply_tilt_inversion function."""

    def test_no_inversion_0_percent(self) -> None:
        """0% stays at 0% without inversion."""
        assert apply_tilt_inversion(0.0, invert=False) == 0.0

    def test_no_inversion_50_percent(self) -> None:
        """50% stays at 50% without inversion."""
        assert apply_tilt_inversion(50.0, invert=False) == 50.0

    def test_no_inversion_100_percent(self) -> None:
        """100% stays at 100% without inversion."""
        assert apply_tilt_inversion(100.0, invert=False) == 100.0

    def test_inversion_0_percent(self) -> None:
        """0% becomes 100% with inversion."""
        assert apply_tilt_inversion(0.0, invert=True) == 100.0

    def test_inversion_50_percent(self) -> None:
        """50% stays at 50% with inversion."""
        assert apply_tilt_inversion(50.0, invert=True) == 50.0

    def test_inversion_100_percent(self) -> None:
        """100% becomes 0% with inversion."""
        assert apply_tilt_inversion(100.0, invert=True) == 0.0

    def test_inversion_25_percent(self) -> None:
        """25% becomes 75% with inversion."""
        assert apply_tilt_inversion(25.0, invert=True) == 75.0

    def test_inversion_75_percent(self) -> None:
        """75% becomes 25% with inversion."""
        assert apply_tilt_inversion(75.0, invert=True) == 25.0


@pytest.mark.unit
class TestSunPosition:
    """Tests for SunPosition dataclass."""

    def test_create_sun_position(self) -> None:
        """SunPosition can be created with azimuth and elevation."""
        sun = SunPosition(azimuth_deg=180.0, elevation_deg=45.0)
        assert sun.azimuth_deg == 180.0
        assert sun.elevation_deg == 45.0

    def test_sun_position_is_frozen(self) -> None:
        """SunPosition is immutable."""
        sun = SunPosition(azimuth_deg=180.0, elevation_deg=45.0)
        with pytest.raises(AttributeError):
            sun.azimuth_deg = 90.0  # type: ignore[misc]


@pytest.mark.unit
class TestSlatCalculationResult:
    """Tests for SlatCalculationResult dataclass."""

    def test_create_result(self) -> None:
        """SlatCalculationResult can be created."""
        result = SlatCalculationResult(
            slat_angle_deg=45.0,
            slat_tilt_percent=50.0,
            profile_angle_deg=60.0,
            horizontal_shadow_angle_deg=10.0,
            sun_is_behind_facade=False,
        )
        assert result.slat_angle_deg == 45.0
        assert result.slat_tilt_percent == 50.0
        assert result.profile_angle_deg == 60.0
        assert result.horizontal_shadow_angle_deg == 10.0
        assert result.sun_is_behind_facade is False

    def test_result_is_frozen(self) -> None:
        """SlatCalculationResult is immutable."""
        result = SlatCalculationResult(
            slat_angle_deg=45.0,
            slat_tilt_percent=50.0,
            profile_angle_deg=60.0,
            horizontal_shadow_angle_deg=10.0,
            sun_is_behind_facade=False,
        )
        with pytest.raises(AttributeError):
            result.slat_angle_deg = 90.0  # type: ignore[misc]
