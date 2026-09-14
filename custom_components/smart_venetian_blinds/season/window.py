"""
Seasonal activity window for a window group.

A window group can be restricted to a recurring part of the year (e.g. 15 March
to 15 October). Outside that window the control pipeline stops driving covers —
see ``SeasonalPausePipe``. The window is year-agnostic: only (month, day) is
compared, so it repeats every year without reconfiguration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from custom_components.smart_venetian_blinds.const import (
    CONF_SEASON_END_DAY,
    CONF_SEASON_END_MONTH,
    CONF_SEASON_PAUSE_ENABLED,
    CONF_SEASON_REST_POSITION,
    CONF_SEASON_START_DAY,
    CONF_SEASON_START_MONTH,
    DEFAULT_SEASON_END_DAY,
    DEFAULT_SEASON_END_MONTH,
    DEFAULT_SEASON_PAUSE_ENABLED,
    DEFAULT_SEASON_REST_POSITION,
    DEFAULT_SEASON_START_DAY,
    DEFAULT_SEASON_START_MONTH,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import date
    from typing import Any

# Days per month for validation; February uses 29 so a leap-day boundary stays configurable.
DAYS_IN_MONTH: dict[int, int] = {
    1: 31,
    2: 29,
    3: 31,
    4: 30,
    5: 31,
    6: 30,
    7: 31,
    8: 31,
    9: 30,
    10: 31,
    11: 30,
    12: 31,
}


def is_valid_month_day(month: int, day: int) -> bool:
    """Return True if the (month, day) pair can occur in a calendar year."""
    if month not in DAYS_IN_MONTH:
        return False
    return 1 <= day <= DAYS_IN_MONTH[month]


@dataclass(frozen=True)
class SeasonWindow:
    """
    Recurring yearly window during which the group actively controls covers.

    The window is inclusive on both ends and wraps across New Year when the start
    date is after the end date (e.g. 01 November to 28 February).
    """

    enabled: bool = DEFAULT_SEASON_PAUSE_ENABLED
    start_month: int = DEFAULT_SEASON_START_MONTH
    start_day: int = DEFAULT_SEASON_START_DAY
    end_month: int = DEFAULT_SEASON_END_MONTH
    end_day: int = DEFAULT_SEASON_END_DAY
    rest_position: int = DEFAULT_SEASON_REST_POSITION

    @classmethod
    def from_options(cls, options: Mapping[str, Any] | None) -> SeasonWindow:
        """Create a SeasonWindow from a config entry's options mapping."""
        options = options or {}
        return cls(
            enabled=bool(options.get(CONF_SEASON_PAUSE_ENABLED, DEFAULT_SEASON_PAUSE_ENABLED)),
            start_month=int(options.get(CONF_SEASON_START_MONTH, DEFAULT_SEASON_START_MONTH)),
            start_day=int(options.get(CONF_SEASON_START_DAY, DEFAULT_SEASON_START_DAY)),
            end_month=int(options.get(CONF_SEASON_END_MONTH, DEFAULT_SEASON_END_MONTH)),
            end_day=int(options.get(CONF_SEASON_END_DAY, DEFAULT_SEASON_END_DAY)),
            rest_position=int(options.get(CONF_SEASON_REST_POSITION, DEFAULT_SEASON_REST_POSITION)),
        )

    @property
    def wraps_year_end(self) -> bool:
        """Return True if the active window spans New Year (start after end)."""
        return (self.start_month, self.start_day) > (self.end_month, self.end_day)

    def is_active(self, today: date) -> bool:
        """Return True if the given date falls inside the active season."""
        if not self.enabled:
            return True

        current = (today.month, today.day)
        start = (self.start_month, self.start_day)
        end = (self.end_month, self.end_day)

        if self.wraps_year_end:
            return current >= start or current <= end
        return start <= current <= end

    def is_paused(self, today: date) -> bool:
        """Return True if the group is seasonally paused on the given date."""
        return not self.is_active(today)

    def describe(self) -> str:
        """Return a human-readable representation of the window (for logs/diagnostics)."""
        return f"{self.start_day:02d}.{self.start_month:02d}-{self.end_day:02d}.{self.end_month:02d}"


__all__ = [
    "DAYS_IN_MONTH",
    "SeasonWindow",
    "is_valid_month_day",
]
