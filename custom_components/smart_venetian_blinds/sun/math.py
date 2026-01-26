"""
Pure math functions for slat angle calculation.

No Home Assistant dependencies - fully unit testable.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class SunPosition:
    """Sun position data."""

    azimuth_deg: float  # 0=N, 90=E, 180=S, 270=W
    elevation_deg: float  # Altitude above horizon


@dataclass(frozen=True, slots=True)
class SlatCalculationResult:
    """Result of slat angle calculation."""

    slat_angle_deg: float  # 0° = horizontal, 90° = closed
    slat_tilt_percent: float  # 0% = closed, 100% = open (default convention)
    profile_angle_deg: float  # Vertical shadow angle (omega)
    horizontal_shadow_angle_deg: float  # HSA
    sun_is_behind_facade: bool  # True if sun doesn't hit this facade


def normalize_angle_180(angle_deg: float) -> float:
    """Normalize angle to [-180, +180] range."""
    angle = angle_deg % 360
    if angle > 180:
        angle -= 360
    return angle


def calculate_slat_angle(
    sun: SunPosition,
    facade_azimuth_deg: float,
    slat_width_mm: float,
    slat_spacing_mm: float,
    min_angle_deg: float = 0.0,
    max_angle_deg: float = 90.0,
) -> SlatCalculationResult | None:
    """
    Calculate optimal slat tilt angle for sun cut-off.

    Args:
        sun: Current sun position (azimuth, elevation).
        facade_azimuth_deg: Azimuth of facade normal (0-359°).
        slat_width_mm: Slat width (L) in millimeters.
        slat_spacing_mm: Slat spacing (d) in millimeters.
        min_angle_deg: Minimum mechanical angle constraint.
        max_angle_deg: Maximum mechanical angle constraint.

    Returns:
        SlatCalculationResult or None if sun is below horizon.

    Coordinate system:
        - Slat angle 0° = horizontal (fully open)
        - Slat angle 90° = vertical (fully closed)
        - Positive angles tilt the outer edge down (standard convention)
    """
    # Guard: Sun below horizon
    if sun.elevation_deg <= 0:
        return None

    # Step A: Horizontal Shadow Angle (HSA)
    hsa_deg = normalize_angle_180(sun.azimuth_deg - facade_azimuth_deg)

    # Sun behind facade - no direct radiation on this window
    if abs(hsa_deg) > 90:
        return SlatCalculationResult(
            slat_angle_deg=0.0,
            slat_tilt_percent=100.0,
            profile_angle_deg=0.0,
            horizontal_shadow_angle_deg=hsa_deg,
            sun_is_behind_facade=True,
        )

    # Step B: Profile Angle (Omega) - vertical shadow angle
    alt_rad = math.radians(sun.elevation_deg)
    hsa_rad = math.radians(hsa_deg)

    # Guard: cos(hsa) near zero (sun nearly parallel to facade)
    cos_hsa = math.cos(hsa_rad)
    if abs(cos_hsa) < 1e-10:
        # Edge case: sun exactly parallel to facade plane
        # Profile angle approaches 90° (sun directly overhead relative to facade)
        omega_rad = math.pi / 2
    else:
        omega_rad = math.atan(math.tan(alt_rad) / cos_hsa)

    omega_deg = math.degrees(omega_rad)

    # Step C: Slat cut-off geometry
    # Solve: sin(theta + omega) = (d * cos(omega)) / L
    L = slat_width_mm
    d = slat_spacing_mm
    cos_omega = math.cos(omega_rad)

    ratio = (d * cos_omega) / L

    # Guard: Geometry impossible (slats can't fully block sun)
    if ratio > 1.0:
        # Slat spacing too large for complete cut-off
        # Use maximum closure angle
        theta_deg = max_angle_deg
    elif ratio < -1.0:
        # Shouldn't happen with valid geometry, but handle gracefully
        theta_deg = min_angle_deg
    else:
        # Normal case: calculate exact cut-off angle
        theta_rad = math.asin(ratio) - omega_rad
        theta_deg = math.degrees(theta_rad)

    # Step D: Apply mechanical constraints
    theta_deg = max(min_angle_deg, min(max_angle_deg, theta_deg))

    # Step E: Convert to percent (0° = 100% open, 90° = 0% open)
    # Clamp theta to [0, 90] for percent calculation
    theta_for_percent = max(0.0, min(90.0, theta_deg))
    slat_tilt_percent = 100.0 * (1.0 - theta_for_percent / 90.0)

    return SlatCalculationResult(
        slat_angle_deg=round(theta_deg, 1),
        slat_tilt_percent=round(slat_tilt_percent, 1),
        profile_angle_deg=round(omega_deg, 1),
        horizontal_shadow_angle_deg=round(hsa_deg, 1),
        sun_is_behind_facade=False,
    )


def apply_tilt_inversion(
    position_percent: float,
    invert: bool,
) -> float:
    """Apply tilt inversion if cover uses reversed semantics."""
    if invert:
        return 100.0 - position_percent
    return position_percent
