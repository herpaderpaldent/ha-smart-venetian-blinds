"""
Group state dataclass for smart_venetian_blinds.

Contains calculation results and state tracking for a window group.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from custom_components.smart_venetian_blinds.sun.math import SlatCalculationResult, SunPosition


@dataclass
class GroupState:
    """
    State container for a window group.

    Holds the current calculation results, last applied values,
    and timing information for throttling.
    """

    # Current sun position
    sun_position: SunPosition | None = None

    # Current calculation result
    calculation: SlatCalculationResult | None = None

    # Last applied values (for throttling comparison)
    last_applied_angle: float | None = None
    last_applied_time: datetime | None = None

    # Auto control state (per group)
    auto_control_enabled: bool = True

    # Cover states for manual close detection (entity_id -> last known position)
    cover_positions: dict[str, float] = field(default_factory=dict)

    def should_apply(
        self,
        new_angle: float,
        threshold_deg: float,
        min_interval_sec: int,
    ) -> bool:
        """
        Determine if new angle should be applied based on throttling rules.

        Args:
            new_angle: The newly calculated slat angle.
            threshold_deg: Minimum angle change to trigger update.
            min_interval_sec: Minimum seconds between updates.

        Returns:
            True if the angle change should be applied.
        """
        # Always apply if never applied before
        if self.last_applied_angle is None or self.last_applied_time is None:
            return True

        # Check minimum interval
        now = datetime.now()
        elapsed = (now - self.last_applied_time).total_seconds()
        if elapsed < min_interval_sec:
            return False

        # Check threshold
        angle_change = abs(new_angle - self.last_applied_angle)
        return angle_change >= threshold_deg

    def mark_applied(self, angle: float) -> None:
        """Mark that an angle was applied."""
        self.last_applied_angle = angle
        self.last_applied_time = datetime.now()

    def reset_throttle(self) -> None:
        """Reset throttle state to allow immediate application."""
        self.last_applied_time = None
